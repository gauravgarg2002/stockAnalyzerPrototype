package com.stockanalyzer.service;

import com.stockanalyzer.domain.AccountCashEntity;
import com.stockanalyzer.domain.AccountCashRepository;
import com.stockanalyzer.domain.HoldingEntity;
import com.stockanalyzer.domain.HoldingRepository;
import com.stockanalyzer.domain.HoldingSource;
import com.stockanalyzer.domain.ImportLogEntity;
import com.stockanalyzer.domain.ImportLogRepository;
import com.stockanalyzer.domain.ImportStatus;
import com.stockanalyzer.engine.model.Kind;
import com.stockanalyzer.python.PythonClient;
import com.stockanalyzer.python.dto.PyDto.BrokerFund;
import com.stockanalyzer.python.dto.PyDto.BrokerPortfolio;
import com.stockanalyzer.python.dto.PyDto.BrokerStock;
import com.stockanalyzer.python.dto.PyDto.BundleResponse;
import com.stockanalyzer.python.dto.PyDto.BundleStock;
import com.stockanalyzer.python.dto.PyDto.StatementFund;
import com.stockanalyzer.python.dto.PyDto.StatementRequest;
import com.stockanalyzer.python.dto.PyDto.StatementResponse;
import com.stockanalyzer.python.dto.PyDto.Unmatched;
import com.stockanalyzer.web.ApiException;
import com.stockanalyzer.web.dto.ConnectDto.ImportResult;
import com.stockanalyzer.web.dto.ConnectDto.UnmatchedView;
import com.stockanalyzer.web.dto.Shared.ImportLogEntry;
import java.io.IOException;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.web.multipart.MultipartFile;

/**
 * Imports from the broker (replaces the KITE rows and the idle cash) and from a statement upload (replaces the
 * STATEMENT rows). MANUAL rows are never touched. Every import clears the response cache.
 */
@Service
public class ImportService {

    static final long MAX_UPLOAD_BYTES = 10L * 1024 * 1024;

    private final PythonClient python;
    private final PortfolioService portfolio;
    private final HoldingRepository holdingRepo;
    private final AccountCashRepository cashRepo;
    private final ImportLogRepository logRepo;
    private final ResponseCache cache;
    private final TransactionTemplate tx;

    public ImportService(PythonClient python, PortfolioService portfolio, HoldingRepository holdingRepo,
                         AccountCashRepository cashRepo, ImportLogRepository logRepo, ResponseCache cache,
                         PlatformTransactionManager txManager) {
        this.python = python;
        this.portfolio = portfolio;
        this.holdingRepo = holdingRepo;
        this.cashRepo = cashRepo;
        this.logRepo = logRepo;
        this.cache = cache;
        this.tx = new TransactionTemplate(txManager);
    }

    static ImportLogEntry toDto(ImportLogEntity e) {
        return new ImportLogEntry(e.getId(), e.getSource().name(), e.getStatus().name(), Times.iso(e.getStartedAt()),
                Times.iso(e.getFinishedAt()), e.getStockCount(), e.getFundCount(), e.getUnmatchedCount(), e.getMessage(),
                e.isSampleData());
    }

    private static LocalDate parseDate(String s) {
        if (s == null || s.isBlank()) return null;
        try {
            return LocalDate.parse(s.trim());
        } catch (DateTimeParseException e) {
            return null;
        }
    }

    private static double firstPositive(Double... values) {
        for (Double v : values) if (v != null && v > 0) return v;
        return 0.0;
    }

    private static String message(int stocks, int funds, int unmatched, boolean cash) {
        String base = "Imported " + stocks + (stocks == 1 ? " stock, " : " stocks, ") + funds
                + (funds == 1 ? " fund" : " funds") + (cash ? " and idle cash." : ".");
        return unmatched == 0 ? base : base + " " + unmatched + (unmatched == 1 ? " item" : " items") + " could not be matched.";
    }

    private static String statementMessage(int funds, int unmatched) {
        String base = "Imported " + funds + (funds == 1 ? " fund" : " funds") + " from your statement.";
        return unmatched == 0 ? base : base + " " + unmatched + (unmatched == 1 ? " item" : " items") + " could not be matched.";
    }

    private static List<UnmatchedView> unmatchedViews(List<Unmatched> list) {
        List<UnmatchedView> out = new ArrayList<>();
        for (Unmatched u : list) out.add(new UnmatchedView(u.name(), u.isin(), u.reason()));
        return out;
    }

    // ---- broker import ------------------------------------------------------------------------------------------

    public ImportResult importFromBroker() {
        OffsetDateTime started = Times.now();
        BrokerPortfolio p = python.brokerPortfolio(); // 409 BROKER_NOT_CONNECTED is re-emitted unchanged
        List<BrokerStock> stocks = p.stocks() == null ? List.of() : p.stocks();
        List<BrokerFund> funds = p.funds() == null ? List.of() : p.funds();

        List<String> symbols = new ArrayList<>();
        for (BrokerStock s : stocks) if (s.symbol() != null) symbols.add(s.symbol().trim().toUpperCase(Locale.ROOT));
        Map<String, BundleStock> known = new LinkedHashMap<>();
        boolean sample = p.sampleData();
        if (!symbols.isEmpty()) {
            BundleResponse b = portfolio.bundle(symbols, List.of());
            sample |= b.sampleData();
            if (b.stocks() != null) for (BundleStock s : b.stocks()) known.put(s.symbol(), s);
        }

        List<UnmatchedView> unmatched = unmatchedViews(p.unmatched() == null ? List.of() : p.unmatched());
        List<HoldingEntity> rows = new ArrayList<>();
        int stockCount = 0;
        int fundCount = 0;
        final boolean sampleFlag = sample;
        OffsetDateTime importedAt = Times.now();
        for (BrokerStock s : stocks) {
            if (s.symbol() == null || s.quantity() == null || !(s.quantity() > 0)) continue;
            String sym = s.symbol().trim().toUpperCase(Locale.ROOT);
            BundleStock b = known.get(sym);
            if (b == null) {
                unmatched.add(new UnmatchedView(sym, s.isin(), "Stock not found in stock list."));
                continue;
            }
            rows.add(row(Kind.STOCK, sym, b.name(), s.quantity(), firstPositive(s.avgPrice(), s.lastPrice()),
                    parseDate(s.firstBuyDate()), HoldingSource.KITE, sampleFlag, importedAt));
            stockCount++;
        }
        for (BrokerFund f : funds) {
            if (f.schemeCode() == null || f.units() == null || !(f.units() > 0)) continue;
            rows.add(row(Kind.FUND, f.schemeCode().trim(), f.name(), f.units(), firstPositive(f.avgNav(), f.lastNav()),
                    parseDate(f.firstBuyDate()), HoldingSource.KITE, sampleFlag, importedAt));
            fundCount++;
        }
        double idle = p.idleCashInr() == null ? 0.0 : p.idleCashInr();
        LocalDate cashAsOf = parseDate(p.asOf());
        final int fStocks = stockCount;
        final int fFunds = fundCount;

        ImportLogEntity log = tx.execute(status -> {
            holdingRepo.deleteBySource(HoldingSource.KITE);
            holdingRepo.saveAll(rows);
            AccountCashEntity cash = cashRepo.findById(AccountCashEntity.SINGLE_ID).orElseGet(AccountCashEntity::new);
            cash.setIdleCashInr(idle);
            cash.setAsOf(cashAsOf);
            cash.setSource("KITE");
            cash.setSampleData(sampleFlag);
            cashRepo.save(cash);
            return logRepo.save(newLog(HoldingSource.KITE, unmatched.isEmpty() ? ImportStatus.SUCCESS : ImportStatus.PARTIAL,
                    started, fStocks, fFunds, unmatched.size(), message(fStocks, fFunds, unmatched.size(), true), sampleFlag));
        });
        cache.clearAll();
        return new ImportResult(sampleFlag, log.getId(), "KITE", log.getStatus().name(), Times.iso(log.getFinishedAt()),
                stockCount, fundCount, idle, unmatched, log.getMessage());
    }

    // ---- statement import ---------------------------------------------------------------------------------------

    public ImportResult importFromStatement(MultipartFile file, String password) {
        if (file == null || file.isEmpty()) throw ApiException.badRequest("Please choose a PDF statement to upload.");
        if (file.getSize() > MAX_UPLOAD_BYTES) throw ApiException.badRequest("The file is larger than 10 MB.");
        String name = file.getOriginalFilename() == null ? "statement.pdf" : file.getOriginalFilename();
        String type = file.getContentType() == null ? "" : file.getContentType().toLowerCase(Locale.ROOT);
        if (!name.toLowerCase(Locale.ROOT).endsWith(".pdf") && !type.contains("pdf")) {
            throw ApiException.badRequest("The statement must be a PDF file.");
        }
        byte[] bytes;
        try {
            bytes = file.getBytes();
        } catch (IOException e) {
            throw ApiException.badRequest("The uploaded file could not be read.");
        }
        OffsetDateTime started = Times.now();
        StatementResponse r = python.parseStatement(new StatementRequest(name, Base64.getEncoder().encodeToString(bytes),
                password == null ? "" : password));
        List<StatementFund> funds = r.funds() == null ? List.of() : r.funds();
        List<UnmatchedView> unmatched = unmatchedViews(r.unmatched() == null ? List.of() : r.unmatched());
        OffsetDateTime importedAt = Times.now();
        List<HoldingEntity> rows = new ArrayList<>();
        for (StatementFund f : funds) {
            if (f.schemeCode() == null || f.units() == null || !(f.units() > 0)) {
                unmatched.add(new UnmatchedView(f.name(), f.isin(), "Fund not found in fund list."));
                continue;
            }
            rows.add(row(Kind.FUND, f.schemeCode().trim(), f.name(), f.units(), firstPositive(f.avgCostNav(), f.nav()),
                    null, HoldingSource.STATEMENT, r.sampleData(), importedAt));
        }
        if (rows.isEmpty()) {
            throw new ApiException(422, "STATEMENT_UNREADABLE", "No mutual funds could be read from this statement.", null);
        }
        final int fundCount = rows.size();
        final boolean sample = r.sampleData();
        ImportLogEntity log = tx.execute(status -> {
            holdingRepo.deleteBySource(HoldingSource.STATEMENT);
            holdingRepo.saveAll(rows);
            return logRepo.save(newLog(HoldingSource.STATEMENT, unmatched.isEmpty() ? ImportStatus.SUCCESS : ImportStatus.PARTIAL,
                    started, 0, fundCount, unmatched.size(), statementMessage(fundCount, unmatched.size()), sample));
        });
        cache.clearAll();
        return new ImportResult(sample, log.getId(), "STATEMENT", log.getStatus().name(), Times.iso(log.getFinishedAt()),
                0, fundCount, null, unmatched, log.getMessage());
    }

    // ---- helpers ------------------------------------------------------------------------------------------------

    private static HoldingEntity row(Kind kind, String id, String name, double qty, double avg, LocalDate buy,
                                     HoldingSource source, boolean sample, OffsetDateTime importedAt) {
        HoldingEntity h = new HoldingEntity();
        h.setKind(kind);
        h.setInstrumentId(id);
        h.setName(name);
        h.setQuantity(qty);
        h.setAvgPrice(avg);
        h.setFirstBuyDate(buy);
        h.setSource(source);
        h.setSampleData(sample);
        h.setImportedAt(importedAt);
        return h;
    }

    private static ImportLogEntity newLog(HoldingSource source, ImportStatus status, OffsetDateTime started, int stocks,
                                          int funds, int unmatched, String message, boolean sample) {
        ImportLogEntity e = new ImportLogEntity();
        e.setSource(source);
        e.setStatus(status);
        e.setStartedAt(started);
        e.setFinishedAt(Times.now());
        e.setStockCount(stocks);
        e.setFundCount(funds);
        e.setUnmatchedCount(unmatched);
        e.setMessage(message);
        e.setSampleData(sample);
        return e;
    }
}
