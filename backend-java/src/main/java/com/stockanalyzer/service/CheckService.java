package com.stockanalyzer.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.stockanalyzer.config.AppProperties;
import com.stockanalyzer.domain.HoldingEntity;
import com.stockanalyzer.domain.HoldingRepository;
import com.stockanalyzer.domain.WatchlistItemEntity;
import com.stockanalyzer.domain.WatchlistItemRepository;
import com.stockanalyzer.engine.Money;
import com.stockanalyzer.engine.OverlapEngine;
import com.stockanalyzer.engine.Units;
import com.stockanalyzer.engine.model.FundInfo;
import com.stockanalyzer.engine.model.Kind;
import com.stockanalyzer.python.PythonClient;
import com.stockanalyzer.python.dto.PyDto.BundleFund;
import com.stockanalyzer.python.dto.PyDto.BundleStock;
import com.stockanalyzer.python.dto.PyDto.FundCheckRequest;
import com.stockanalyzer.python.dto.PyDto.FundCheckUserFund;
import com.stockanalyzer.service.PortfolioService.GroupedHolding;
import com.stockanalyzer.service.PortfolioService.Resolved;
import com.stockanalyzer.service.PortfolioService.Snapshot;
import com.stockanalyzer.web.ApiException;
import com.stockanalyzer.web.dto.Shared.Comparison;
import com.stockanalyzer.web.dto.Shared.Figure;
import com.stockanalyzer.web.dto.Shared.UserBlock;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.List;
import java.util.Optional;
import org.springframework.stereotype.Service;

/**
 * Pass-through checks from Python (cached), with the "user" block added by Java. For funds, Java first computes the
 * overlap of the fund with every other fund the user holds and sends it to Python.
 */
@Service
public class CheckService {

    private record AmountChoice(double amount, String basis) { }

    private final PythonClient python;
    private final ResponseCache cache;
    private final PortfolioService portfolio;
    private final HoldingRepository holdingRepo;
    private final WatchlistItemRepository watchRepo;
    private final ObjectMapper mapper;
    private final AppProperties props;

    public CheckService(PythonClient python, ResponseCache cache, PortfolioService portfolio,
                        HoldingRepository holdingRepo, WatchlistItemRepository watchRepo, ObjectMapper mapper,
                        AppProperties props) {
        this.python = python;
        this.cache = cache;
        this.portfolio = portfolio;
        this.holdingRepo = holdingRepo;
        this.watchRepo = watchRepo;
        this.mapper = mapper;
        this.props = props;
    }

    private String json(Object o) {
        try {
            return mapper.writeValueAsString(o);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException(e);
        }
    }

    // ---- search, glossary, explain, compare (pass-through) -------------------------------------------------------

    public JsonNode search(String q) {
        String text = q == null ? "" : q.trim();
        if (text.isEmpty()) throw ApiException.badRequest("q must have at least 1 character.");
        return cache.get("search:" + text, JsonNode.class, () -> python.search(text, 10));
    }

    public JsonNode glossary() {
        return cache.get("glossary", JsonNode.class, python::glossary);
    }

    public JsonNode explain(String term, String kindText, String idText) {
        if (term == null || term.isBlank()) throw ApiException.badRequest("term is required.");
        boolean hasKind = kindText != null && !kindText.isBlank();
        boolean hasId = idText != null && !idText.isBlank();
        if (hasKind != hasId) throw ApiException.badRequest("Give both kind and id, or neither.");
        String t = term.trim();
        if (!hasKind) {
            return cache.get("explain:" + t + "::", JsonNode.class, () -> python.explain(t, null, null));
        }
        Kind kind = Instruments.parseKind(kindText);
        String id = Instruments.normalize(kind, idText);
        return cache.get("explain:" + t + ":" + kind + ":" + id, JsonNode.class, () -> python.explain(t, kind.name(), id));
    }

    public JsonNode compare(String kindText, String idsCsv, Double amountParam) {
        Kind kind = Instruments.parseKind(kindText);
        if (idsCsv == null) throw ApiException.badRequest("ids is required.");
        List<String> ids = Arrays.stream(idsCsv.split(","))
                .map(String::trim)
                .filter(x -> !x.isEmpty())
                .map(x -> Instruments.normalize(kind, x))
                .distinct()
                .toList();
        if (ids.size() < 2 || ids.size() > 3) throw ApiException.badRequest("Give 2 or 3 different ids to compare.");
        Double amount = null;
        if (kind == Kind.FUND) {
            double a = amountParam != null ? amountParam : props.app().defaultIllustrativeAmountInr();
            Instruments.checkAmount(a, "amount");
            amount = Money.round2(a);
        }
        final Double amt = amount;
        String csv = String.join(",", ids);
        return cache.get("compare:" + kind + ":" + csv + ":" + (amt == null ? "-" : amt), JsonNode.class,
                () -> python.compare(kind.name(), csv, amt));
    }

    // ---- stock check -------------------------------------------------------------------------------------------

    public JsonNode stockCheck(String symbolText) {
        String sym = Instruments.normalize(Kind.STOCK, symbolText);
        JsonNode body = cache.get("stock-check:" + sym, JsonNode.class, () -> python.stockCheck(sym));
        double qty = heldQuantity(Kind.STOCK, sym);
        Figure value = null;
        if (qty > 0) {
            BundleStock b = portfolio.resolve(Kind.STOCK, sym).stock();
            if (b != null && b.lastPrice() != null) {
                value = holdingValue(qty * b.lastPrice(), b.priceOneYearAgo() == null ? null : qty * b.priceOneYearAgo(),
                        b.lastPriceDate());
            }
        }
        return withUser(body, userBlock(Kind.STOCK, sym, qty, value));
    }

    // ---- fund check --------------------------------------------------------------------------------------------

    public JsonNode fundCheck(String codeText, Double amountParam) {
        String code = Instruments.normalize(Kind.FUND, codeText);
        if (amountParam != null) Instruments.checkAmount(amountParam, "amount");
        Snapshot snap = portfolio.snapshot();
        FundInfo target = snap.input().funds().get(code);
        BundleFund bundleFund = snap.fundBundle().get(code);
        if (target == null) {
            Resolved r = portfolio.resolve(Kind.FUND, code);
            target = PortfolioService.toFundInfo(r.fund());
            bundleFund = r.fund();
        }
        double units = 0;
        List<FundCheckUserFund> userFunds = new ArrayList<>();
        for (GroupedHolding g : snap.groups()) {
            if (g.kind() != Kind.FUND) continue;
            if (g.id().equals(code)) {
                units = g.quantity();
                continue;
            }
            FundInfo other = snap.input().funds().get(g.id());
            if (other == null) continue;
            OverlapEngine.OverlapResult o = OverlapEngine.overlap(target, other);
            userFunds.add(new FundCheckUserFund(other.schemeCode(), other.name(), o.pct(), o.commonCount()));
        }
        userFunds.sort(Comparator.comparingDouble(FundCheckUserFund::overlapPct).reversed()
                .thenComparing(FundCheckUserFund::schemeCode));

        AmountChoice choice;
        if (amountParam != null) {
            choice = new AmountChoice(Money.round2(amountParam), "USER_INPUT");
        } else if (units > 0 && target.nav() > 0) {
            choice = new AmountChoice(Money.round2(units * target.nav()), "HOLDING");
        } else {
            choice = new AmountChoice((double) props.app().defaultIllustrativeAmountInr(), "ILLUSTRATIVE");
        }
        FundCheckRequest request = new FundCheckRequest(choice.amount(), choice.basis(), userFunds);
        String key = "fund-check:" + code + ":" + choice.amount() + ":" + choice.basis() + ":" + ResponseCache.hash(json(userFunds));
        JsonNode body = cache.get(key, JsonNode.class, () -> python.fundCheck(code, request));

        Figure value = null;
        if (units > 0 && target.nav() > 0) {
            value = holdingValue(units * target.nav(),
                    bundleFund != null && bundleFund.navOneYearAgo() != null ? units * bundleFund.navOneYearAgo() : null,
                    bundleFund == null ? null : bundleFund.navDate());
        }
        return withUser(body, userBlock(Kind.FUND, code, units, value));
    }

    // ---- user block --------------------------------------------------------------------------------------------

    private double heldQuantity(Kind kind, String id) {
        double q = 0;
        for (HoldingEntity h : holdingRepo.findByKindAndInstrumentIdOrderByIdAsc(kind, id)) q += h.getQuantity();
        return q;
    }

    private Figure holdingValue(double valueInr, Double valueOneYearAgo, String asOf) {
        List<Comparison> cmp = new ArrayList<>();
        if (valueOneYearAgo != null) cmp.add(Figures.cmp("PREVIOUS_PERIOD", "1 year ago", Money.roundRupees(valueOneYearAgo), Units.INR));
        return Figures.calc("holding_value", "Value of your holding", Money.roundRupees(valueInr), Units.INR, asOf, cmp);
    }

    private UserBlock userBlock(Kind kind, String id, double quantity, Figure value) {
        Optional<WatchlistItemEntity> w = watchRepo.findByKindAndInstrumentId(kind, id);
        boolean holds = quantity > 0;
        return new UserBlock(holds, holds ? quantity : null, holds ? value : null,
                w.map(WatchlistItemEntity::getId).orElse(null), w.map(WatchlistItemEntity::getNote).orElse(null));
    }

    private JsonNode withUser(JsonNode body, UserBlock user) {
        if (!(body instanceof ObjectNode)) throw ApiException.internal("Unexpected response from the data service.");
        ObjectNode copy = ((ObjectNode) body).deepCopy();
        copy.set("user", mapper.valueToTree(user));
        return copy;
    }
}
