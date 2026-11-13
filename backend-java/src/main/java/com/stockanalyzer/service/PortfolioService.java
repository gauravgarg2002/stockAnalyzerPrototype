package com.stockanalyzer.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.stockanalyzer.config.AppProperties;
import com.stockanalyzer.domain.AccountCashEntity;
import com.stockanalyzer.domain.AccountCashRepository;
import com.stockanalyzer.domain.HoldingEntity;
import com.stockanalyzer.domain.HoldingRepository;
import com.stockanalyzer.domain.HoldingSource;
import com.stockanalyzer.domain.ImportLogRepository;
import com.stockanalyzer.domain.ImportStatus;
import com.stockanalyzer.engine.MapPricePoints;
import com.stockanalyzer.engine.NarrateItem;
import com.stockanalyzer.engine.NarrationPlan;
import com.stockanalyzer.engine.PortfolioEngine;
import com.stockanalyzer.engine.PortfolioResult;
import com.stockanalyzer.engine.PricePoints;
import com.stockanalyzer.engine.ReturnsEngine;
import com.stockanalyzer.engine.model.AssetMix;
import com.stockanalyzer.engine.model.FundConstituent;
import com.stockanalyzer.engine.model.FundInfo;
import com.stockanalyzer.engine.model.Kind;
import com.stockanalyzer.engine.model.PortfolioInput;
import com.stockanalyzer.engine.model.Position;
import com.stockanalyzer.engine.model.SizeBand;
import com.stockanalyzer.engine.model.StockInfo;
import com.stockanalyzer.python.PythonClient;
import com.stockanalyzer.python.dto.PyDto.BundleFund;
import com.stockanalyzer.python.dto.PyDto.BundleHolding;
import com.stockanalyzer.python.dto.PyDto.BundleResponse;
import com.stockanalyzer.python.dto.PyDto.BundleStock;
import com.stockanalyzer.python.dto.PyDto.NarrateResponse;
import com.stockanalyzer.python.dto.PyDto.NarrateResultItem;
import com.stockanalyzer.python.dto.PyDto.PointsItem;
import com.stockanalyzer.python.dto.PyDto.PointsRequest;
import com.stockanalyzer.python.dto.PyDto.PointsResponse;
import com.stockanalyzer.python.dto.PyDto.PointsResultItem;
import com.stockanalyzer.python.dto.PyDto.PointValue;
import com.stockanalyzer.web.ApiException;
import com.stockanalyzer.web.dto.PortfolioDto.PortfolioResponse;
import com.stockanalyzer.web.dto.Shared.Sentence;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.TreeSet;
import org.springframework.stereotype.Service;

/**
 * Holdings, then instrument bundle and price points from Python, then the pure engine, then sentences from Python.
 * Every portfolio number is computed by the engine; Java writes no sentences.
 */
@Service
public class PortfolioService {

    /** One instrument across all of its holding rows. */
    public record GroupedHolding(Kind kind, String id, String name, double quantity, double avgPrice,
                                 LocalDate firstBuyDate, List<Long> ids, List<String> sources, boolean sampleData) { }

    /** The user's holdings with their instrument data, ready for the engine. */
    public record Snapshot(PortfolioInput input, List<GroupedHolding> groups, Map<String, BundleStock> stockBundle,
                           Map<String, BundleFund> fundBundle, boolean sampleData, boolean connected, LocalDate asOf) { }

    private final HoldingRepository holdingRepo;
    private final AccountCashRepository cashRepo;
    private final ImportLogRepository importRepo;
    private final PythonClient python;
    private final ResponseCache cache;
    private final ObjectMapper mapper;
    private final AppProperties props;

    public PortfolioService(HoldingRepository holdingRepo, AccountCashRepository cashRepo,
                            ImportLogRepository importRepo, PythonClient python, ResponseCache cache,
                            ObjectMapper mapper, AppProperties props) {
        this.holdingRepo = holdingRepo;
        this.cashRepo = cashRepo;
        this.importRepo = importRepo;
        this.python = python;
        this.cache = cache;
        this.mapper = mapper;
        this.props = props;
    }

    // ---- python helpers (cached) --------------------------------------------------------------------------------

    /** B.8 bundle, cached under bundle:{sorted ids}. */
    public BundleResponse bundle(List<String> stocks, List<String> funds) {
        List<String> s = new ArrayList<>(new TreeSet<>(stocks));
        List<String> f = new ArrayList<>(new TreeSet<>(funds));
        String key = "bundle:S:" + String.join(",", s) + "|F:" + String.join(",", f);
        return cache.get(key, BundleResponse.class, () -> python.bundle(s, f));
    }

    private String json(Object o) {
        try {
            return mapper.writeValueAsString(o);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException(e);
        }
    }

    /** B.9 price points for everything the returns engine needs, cached under points:{hash}. */
    PricePoints points(PortfolioInput input) {
        List<PointsItem> items = new ArrayList<>();
        for (ReturnsEngine.PointRequest r : ReturnsEngine.pointRequests(input)) {
            List<String> dates = new ArrayList<>();
            for (LocalDate d : r.dates()) dates.add(d.toString());
            items.add(new PointsItem(r.kind(), r.id(), dates));
        }
        PointsRequest request = new PointsRequest(items);
        PointsResponse response = cache.get("points:" + ResponseCache.hash(json(request)), PointsResponse.class,
                () -> python.points(request));
        MapPricePoints out = new MapPricePoints();
        if (response != null && response.items() != null) {
            for (PointsResultItem it : response.items()) {
                if (it.values() == null) continue;
                for (PointValue v : it.values()) {
                    if (v.value() != null && v.requestedDate() != null) {
                        out.put(it.kind(), it.id(), LocalDate.parse(v.requestedDate()), v.value());
                    }
                }
            }
        }
        return out;
    }

    /** B.12: one narrate call for a page. Returns sentences by item key. */
    public Map<String, Sentence> narrate(List<NarrateItem> items) {
        Map<String, Sentence> out = new LinkedHashMap<>();
        if (items.isEmpty()) return out;
        NarrateResponse r = python.narrate(items, props.llmConfigured());
        if (r != null && r.items() != null) {
            for (NarrateResultItem i : r.items()) out.put(i.key(), i.sentence());
        }
        return out;
    }

    // ---- bundle to engine types ---------------------------------------------------------------------------------

    public static StockInfo toStockInfo(BundleStock b) {
        return new StockInfo(b.symbol(), b.name(), b.sector(), SizeBand.parse(b.sizeBand()),
                b.lastPrice() == null ? 0.0 : b.lastPrice(), b.checkAvailable());
    }

    public static FundInfo toFundInfo(BundleFund b) {
        List<FundConstituent> cs = new ArrayList<>();
        if (b.holdings() != null) {
            for (BundleHolding h : b.holdings()) {
                cs.add(new FundConstituent(h.key(), h.symbol(), h.name(), h.sector(), SizeBand.parse(h.sizeBand()),
                        h.weightPct() == null ? 0.0 : h.weightPct(), h.checkAvailable()));
            }
        }
        AssetMix mix = b.assetMix() == null ? new AssetMix(0, 0, 0, 0)
                : new AssetMix(b.assetMix().equityPct(), b.assetMix().debtPct(), b.assetMix().cashPct(), b.assetMix().otherPct());
        LocalDate pd = b.portfolioDate() == null ? null : LocalDate.parse(b.portfolioDate());
        return new FundInfo(b.schemeCode(), b.name(), b.category(), b.planType(), b.terPct(), b.twinSchemeCode(),
                b.twinName(), b.twinTerPct(), b.categoryMedianTerPct(), b.nav() == null ? 0.0 : b.nav(), mix, pd, cs);
    }

    /** One instrument looked up in the bundle. Exactly one of stock and fund is set. */
    public record Resolved(Kind kind, String id, String name, String subtitle, BundleStock stock, BundleFund fund,
                           boolean sampleData) { }

    /** Looks an instrument up via the bundle; 404 NOT_FOUND when Python does not know it. */
    public Resolved resolve(Kind kind, String id) {
        if (kind == Kind.STOCK) {
            BundleResponse b = bundle(List.of(id), List.of());
            if (b.stocks() != null) {
                for (BundleStock s : b.stocks()) {
                    if (id.equals(s.symbol())) return new Resolved(kind, id, s.name(), s.subtitle(), s, null, b.sampleData());
                }
            }
            throw ApiException.notFound("No stock found for symbol " + id + ".", Map.of("symbol", id));
        }
        BundleResponse b = bundle(List.of(), List.of(id));
        if (b.funds() != null) {
            for (BundleFund f : b.funds()) {
                if (id.equals(f.schemeCode())) return new Resolved(kind, id, f.name(), f.subtitle(), null, f, b.sampleData());
            }
        }
        throw ApiException.notFound("No fund found for scheme code " + id + ".", Map.of("schemeCode", id));
    }

    // ---- snapshot -----------------------------------------------------------------------------------------------

    public Snapshot snapshot() {
        List<HoldingEntity> all = holdingRepo.findAllByOrderByIdAsc();
        Map<String, List<HoldingEntity>> byInstrument = new LinkedHashMap<>();
        for (HoldingEntity h : all) {
            byInstrument.computeIfAbsent(h.getKind() + "|" + h.getInstrumentId(), k -> new ArrayList<>()).add(h);
        }
        List<GroupedHolding> groups = new ArrayList<>();
        List<String> stockIds = new ArrayList<>();
        List<String> fundIds = new ArrayList<>();
        for (List<HoldingEntity> rows : byInstrument.values()) {
            HoldingEntity first = rows.get(0);
            double qty = 0, costSum = 0;
            LocalDate earliest = null;
            List<Long> ids = new ArrayList<>();
            Set<HoldingSource> sources = new TreeSet<>();
            boolean sample = false;
            for (HoldingEntity h : rows) {
                qty += h.getQuantity();
                costSum += h.getQuantity() * h.getAvgPrice();
                if (h.getFirstBuyDate() != null && (earliest == null || h.getFirstBuyDate().isBefore(earliest))) {
                    earliest = h.getFirstBuyDate();
                }
                ids.add(h.getId());
                sources.add(h.getSource());
                sample |= h.isSampleData();
            }
            if (!(qty > 0)) continue;
            List<String> sourceNames = new ArrayList<>();
            for (HoldingSource s : sources) sourceNames.add(s.name());
            groups.add(new GroupedHolding(first.getKind(), first.getInstrumentId(), first.getName(), qty, costSum / qty,
                    earliest, ids, sourceNames, sample));
            (first.getKind() == Kind.STOCK ? stockIds : fundIds).add(first.getInstrumentId());
        }
        BundleResponse bundle = bundle(stockIds, fundIds);
        Map<String, BundleStock> stockBundle = new LinkedHashMap<>();
        Map<String, BundleFund> fundBundle = new LinkedHashMap<>();
        Map<String, StockInfo> stockInfos = new LinkedHashMap<>();
        Map<String, FundInfo> fundInfos = new LinkedHashMap<>();
        if (bundle.stocks() != null) {
            for (BundleStock s : bundle.stocks()) {
                stockBundle.put(s.symbol(), s);
                stockInfos.put(s.symbol(), toStockInfo(s));
            }
        }
        if (bundle.funds() != null) {
            for (BundleFund f : bundle.funds()) {
                fundBundle.put(f.schemeCode(), f);
                fundInfos.put(f.schemeCode(), toFundInfo(f));
            }
        }
        List<Position> positions = new ArrayList<>();
        boolean sample = bundle.sampleData();
        for (GroupedHolding g : groups) {
            boolean known = g.kind() == Kind.STOCK ? stockInfos.containsKey(g.id()) : fundInfos.containsKey(g.id());
            if (!known) continue;
            positions.add(new Position(g.kind(), g.id(), g.quantity(), g.avgPrice(), g.firstBuyDate()));
            sample |= g.sampleData();
        }
        Optional<AccountCashEntity> cash = cashRepo.findById(AccountCashEntity.SINGLE_ID);
        double idle = cash.map(AccountCashEntity::getIdleCashInr).orElse(0.0);
        sample |= cash.map(AccountCashEntity::isSampleData).orElse(false);
        LocalDate asOf = bundle.asOf() != null ? LocalDate.parse(bundle.asOf()) : LocalDate.parse(props.app().sampleAsOf());
        boolean connected = importRepo.countBySourceAndStatusNot(HoldingSource.KITE, ImportStatus.FAILED) > 0;
        PortfolioInput input = new PortfolioInput(positions, stockInfos, fundInfos, idle, asOf);
        return new Snapshot(input, Collections.unmodifiableList(groups), stockBundle, fundBundle, sample, connected, asOf);
    }

    /** Runs the engine on a snapshot (with returns when there are holdings). */
    public PortfolioResult compute(Snapshot snap) {
        PricePoints pts = snap.input().positions().isEmpty() ? null : points(snap.input());
        return PortfolioEngine.compute(snap.input(), pts);
    }

    public PortfolioResponse portfolio() {
        Snapshot snap = snapshot();
        PortfolioResult result = compute(snap);
        Map<String, Sentence> sentences = narrate(NarrationPlan.forPortfolio(result));
        return PortfolioViews.portfolio(snap, result, sentences);
    }
}
