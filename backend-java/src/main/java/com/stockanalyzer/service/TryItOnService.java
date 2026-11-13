package com.stockanalyzer.service;

import com.stockanalyzer.engine.IndianFormat;
import com.stockanalyzer.engine.NarrationPlan;
import com.stockanalyzer.engine.PortfolioResult;
import com.stockanalyzer.engine.TryItOnEngine;
import com.stockanalyzer.engine.TryItOnEngine.Mode;
import com.stockanalyzer.engine.TryItOnEngine.TryItOnResult;
import com.stockanalyzer.engine.Units;
import com.stockanalyzer.engine.model.FundInfo;
import com.stockanalyzer.engine.model.Kind;
import com.stockanalyzer.engine.model.PortfolioInput;
import com.stockanalyzer.engine.model.StockInfo;
import com.stockanalyzer.service.PortfolioService.Resolved;
import com.stockanalyzer.service.PortfolioService.Snapshot;
import com.stockanalyzer.web.ApiException;
import com.stockanalyzer.web.dto.Shared.Figure;
import com.stockanalyzer.web.dto.Shared.InstrumentRef;
import com.stockanalyzer.web.dto.Shared.Sentence;
import com.stockanalyzer.web.dto.TryItOnDto.CostMetrics;
import com.stockanalyzer.web.dto.TryItOnDto.FigureBeforeAfter;
import com.stockanalyzer.web.dto.TryItOnDto.FundOverlapView;
import com.stockanalyzer.web.dto.TryItOnDto.Input;
import com.stockanalyzer.web.dto.TryItOnDto.Metrics;
import com.stockanalyzer.web.dto.TryItOnDto.NamedBeforeAfter;
import com.stockanalyzer.web.dto.TryItOnDto.NamedFigure;
import com.stockanalyzer.web.dto.TryItOnDto.OverlapMetrics;
import com.stockanalyzer.web.dto.TryItOnDto.Request;
import com.stockanalyzer.web.dto.TryItOnDto.Response;
import com.stockanalyzer.web.dto.TryItOnDto.SizeMixBeforeAfter;
import com.stockanalyzer.web.dto.TryItOnDto.StockInFundView;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import org.springframework.stereotype.Service;

/** Try it on (contract A.8): the same engine path as /api/portfolio, run before and after adding the candidate. */
@Service
public class TryItOnService {

    private final PortfolioService portfolio;

    public TryItOnService(PortfolioService portfolio) {
        this.portfolio = portfolio;
    }

    private static Figure beforeAfter(String id, String label, Object value, String unit, Object beforeValue, String asOf) {
        return Figures.calc(id, label, value, unit, asOf, PortfolioViews.one(Figures.cmp("PREVIOUS_PERIOD", "Before", beforeValue, unit)));
    }

    private static FigureBeforeAfter pair(String id, String label, Object before, Object after, String unit, String asOf) {
        return new FigureBeforeAfter(beforeAfter(id, label, before, unit, before, asOf), beforeAfter(id, label, after, unit, before, asOf));
    }

    public Response run(Request req) {
        if (req == null) throw ApiException.badRequest("A request body is required.");
        Kind kind = Instruments.parseKind(req.kind());
        String id = Instruments.normalize(kind, req.id());
        Mode mode;
        String modeText = req.mode() == null ? "" : req.mode().trim().toUpperCase(Locale.ROOT);
        if (modeText.equals("LUMP_SUM")) mode = Mode.LUMP_SUM;
        else if (modeText.equals("SIP")) mode = Mode.SIP;
        else throw ApiException.badRequest("mode must be LUMP_SUM or SIP.");
        if (req.amountInr() == null) throw ApiException.badRequest("amountInr is required.");
        Instruments.checkAmount(req.amountInr(), "amountInr");
        Integer months = null;
        if (mode == Mode.SIP) {
            months = req.months() == null ? 12 : req.months();
            if (months < 1 || months > 60) throw ApiException.badRequest("months must be between 1 and 60.");
        }

        Resolved cand = portfolio.resolve(kind, id);
        Snapshot snap = portfolio.snapshot();
        Map<String, StockInfo> stocks = new LinkedHashMap<>(snap.input().stocks());
        Map<String, FundInfo> funds = new LinkedHashMap<>(snap.input().funds());
        if (kind == Kind.STOCK) stocks.put(id, PortfolioService.toStockInfo(cand.stock()));
        else funds.put(id, PortfolioService.toFundInfo(cand.fund()));
        PortfolioInput input = new PortfolioInput(snap.input().positions(), stocks, funds, snap.input().idleCashInr(), snap.asOf());

        TryItOnResult result;
        try {
            result = TryItOnEngine.run(input, kind, id, mode, req.amountInr(), months);
        } catch (IllegalArgumentException e) {
            throw ApiException.badRequest("This amount cannot be tried on this instrument.");
        }
        Map<String, Sentence> s = portfolio.narrate(NarrationPlan.forTryItOn(result));
        return view(snap, cand, result, s);
    }

    private Response view(Snapshot snap, Resolved cand, TryItOnResult t, Map<String, Sentence> s) {
        String asOf = snap.asOf().toString();
        PortfolioResult b = t.before();
        PortfolioResult a = t.after();

        NamedBeforeAfter largest = new NamedBeforeAfter(
                new NamedFigure(b.concentration().largestName(), beforeAfter("largest_company", "Largest company exposure",
                        b.concentration().largestBp() / 100.0, Units.PCT, b.concentration().largestBp() / 100.0, asOf)),
                new NamedFigure(a.concentration().largestName(), beforeAfter("largest_company", "Largest company exposure",
                        a.concentration().largestBp() / 100.0, Units.PCT, b.concentration().largestBp() / 100.0, asOf)));
        NamedBeforeAfter sector = new NamedBeforeAfter(
                new NamedFigure(b.concentration().topSectorName(), beforeAfter("top_sector", "Largest sector",
                        b.concentration().topSectorBp() / 100.0, Units.PCT, b.concentration().topSectorBp() / 100.0, asOf)),
                new NamedFigure(a.concentration().topSectorName(), beforeAfter("top_sector", "Largest sector",
                        a.concentration().topSectorBp() / 100.0, Units.PCT, b.concentration().topSectorBp() / 100.0, asOf)));

        List<FundOverlapView> fundOverlaps = new ArrayList<>();
        for (TryItOnEngine.FundOverlap o : t.fundOverlaps()) {
            fundOverlaps.add(new FundOverlapView(o.schemeCode(), o.name(),
                    Figures.calc("overlap_" + o.schemeCode(), "Overlap with this fund", o.pct(), Units.PCT, asOf, List.of(), "fund_overlap")));
        }
        List<StockInFundView> stockInFunds = new ArrayList<>();
        for (TryItOnEngine.StockInFund f : t.stockInFunds()) {
            stockInFunds.add(new StockInFundView(f.schemeCode(), f.name(),
                    Figures.calc("weight_in_fund", "Weight inside this fund", f.weightPct(), Units.PCT, asOf, List.of())));
        }
        FigureBeforeAfter exposure = t.kind() == Kind.STOCK
                ? pair("candidate_exposure", "Your total exposure to this company", t.exposureBeforeBp() / 100.0,
                        t.exposureAfterBp() / 100.0, Units.PCT, asOf)
                : null;

        long costBefore = b.cost().totalYearlyInr();
        long costAfter = a.cost().totalYearlyInr();
        CostMetrics cost = new CostMetrics(
                beforeAfter("yearly_fund_cost", "Yearly fund fees", costBefore, Units.INR, costBefore, asOf),
                beforeAfter("yearly_fund_cost", "Yearly fund fees", costAfter, Units.INR, costBefore, asOf),
                beforeAfter("yearly_fund_cost_change", "Change in yearly fund fees", costAfter - costBefore, Units.INR, costBefore, asOf));

        Metrics metrics = new Metrics(largest, sector,
                new SizeMixBeforeAfter(PortfolioViews.mix(b.sizeMix()), PortfolioViews.mix(a.sizeMix())),
                pair("holding_count", "Number of holdings", (long) b.holdingCount(), (long) a.holdingCount(), Units.COUNT, asOf),
                new OverlapMetrics(t.kind().name(), fundOverlaps, stockInFunds, exposure), cost);

        Input input = new Input(t.mode().name(), t.amountInr(), t.months(), t.addedValueInr(),
                IndianFormat.formatInr(t.addedValueInr()), t.alreadyHeld());
        return new Response(snap.sampleData() || cand.sampleData(), asOf,
                new InstrumentRef(t.kind().name(), t.id(), t.name(), cand.subtitle()), input,
                s.get(NarrationPlan.TIO_ASSUMPTION), metrics,
                PortfolioViews.pick(s, NarrationPlan.TIO_LARGEST_COMPANY, NarrationPlan.TIO_TOP_SECTOR,
                        NarrationPlan.TIO_SIZE_MIX, NarrationPlan.TIO_HOLDINGS_COUNT, NarrationPlan.TIO_OVERLAP,
                        NarrationPlan.TIO_COST));
    }
}
