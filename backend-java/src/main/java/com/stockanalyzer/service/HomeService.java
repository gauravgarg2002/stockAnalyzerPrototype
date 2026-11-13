package com.stockanalyzer.service;

import com.stockanalyzer.domain.ImportLogEntity;
import com.stockanalyzer.domain.ImportLogRepository;
import com.stockanalyzer.engine.NarrationPlan;
import com.stockanalyzer.engine.PortfolioResult;
import com.stockanalyzer.service.PortfolioService.Snapshot;
import com.stockanalyzer.web.dto.PortfolioDto.HomeResponse;
import com.stockanalyzer.web.dto.Shared.ImportLogEntry;
import com.stockanalyzer.web.dto.Shared.Sentence;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Service;

@Service
public class HomeService {

    private final PortfolioService portfolio;
    private final WatchlistService watchlist;
    private final ImportLogRepository importLogs;

    public HomeService(PortfolioService portfolio, WatchlistService watchlist, ImportLogRepository importLogs) {
        this.portfolio = portfolio;
        this.watchlist = watchlist;
        this.importLogs = importLogs;
    }

    public HomeResponse home() {
        Snapshot snap = portfolio.snapshot();
        PortfolioResult r = portfolio.compute(snap);
        Map<String, Sentence> s = portfolio.narrate(NarrationPlan.forHome(r));
        List<Sentence> summary = r.hasHoldings()
                ? PortfolioViews.pick(s, NarrationPlan.SUMMARY_VALUE, NarrationPlan.SUMMARY_TOP_EXPOSURE, NarrationPlan.SUMMARY_RETURNS)
                : PortfolioViews.pick(s, NarrationPlan.SUMMARY_VALUE);
        List<ImportLogEntity> last = importLogs.findTop1ByOrderByIdDesc();
        ImportLogEntry lastImport = last.isEmpty() ? null : ImportService.toDto(last.get(0));
        return new HomeResponse(snap.sampleData(), snap.asOf().toString(), snap.connected(), r.hasHoldings(), summary,
                r.hasHoldings() ? PortfolioViews.topCompanies(r, 5) : List.of(),
                PortfolioViews.facts(r, s), watchlist.newestFive(), lastImport);
    }
}
