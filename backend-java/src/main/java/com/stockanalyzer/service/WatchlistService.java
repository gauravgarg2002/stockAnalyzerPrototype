package com.stockanalyzer.service;

import com.stockanalyzer.domain.WatchlistItemEntity;
import com.stockanalyzer.domain.WatchlistItemRepository;
import com.stockanalyzer.engine.Units;
import com.stockanalyzer.engine.model.Kind;
import com.stockanalyzer.python.dto.PyDto.BundleFund;
import com.stockanalyzer.python.dto.PyDto.BundleResponse;
import com.stockanalyzer.python.dto.PyDto.BundleStock;
import com.stockanalyzer.service.PortfolioService.Resolved;
import com.stockanalyzer.web.ApiException;
import com.stockanalyzer.web.dto.Shared.Comparison;
import com.stockanalyzer.web.dto.Shared.Figure;
import com.stockanalyzer.web.dto.Shared.WatchlistItem;
import com.stockanalyzer.web.dto.Shared.WatchlistItemResponse;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.springframework.stereotype.Service;

/** Saved instruments with the user's note. Name, subtitle and latest price come from the Python bundle. */
@Service
public class WatchlistService {

    public static final int MAX_NOTE = 1000;

    public record Listed(boolean sampleData, List<WatchlistItem> items) { }

    public record Saved(WatchlistItemResponse item, boolean created) { }

    private final WatchlistItemRepository repo;
    private final PortfolioService portfolio;

    public WatchlistService(WatchlistItemRepository repo, PortfolioService portfolio) {
        this.repo = repo;
        this.portfolio = portfolio;
    }

    private static String checkPath(WatchlistItemEntity e) {
        return (e.getKind() == Kind.STOCK ? "/stock/" : "/fund/") + e.getInstrumentId();
    }

    private static Figure latest(WatchlistItemEntity e, Map<String, BundleStock> stocks, Map<String, BundleFund> funds) {
        if (e.getKind() == Kind.STOCK) {
            BundleStock b = stocks.get(e.getInstrumentId());
            if (b == null || b.lastPrice() == null) return null;
            List<Comparison> cmp = new ArrayList<>();
            if (b.priceOneYearAgo() != null) cmp.add(Figures.cmp("PREVIOUS_PERIOD", "1 year ago", b.priceOneYearAgo(), Units.INR_PRICE));
            return Figures.of("last_price", "Last price", b.lastPrice(), Units.INR_PRICE, b.source(), b.lastPriceDate(), cmp, null);
        }
        BundleFund b = funds.get(e.getInstrumentId());
        if (b == null || b.nav() == null) return null;
        List<Comparison> cmp = new ArrayList<>();
        if (b.navOneYearAgo() != null) cmp.add(Figures.cmp("PREVIOUS_PERIOD", "1 year ago", b.navOneYearAgo(), Units.INR_PRICE));
        return Figures.of("nav", "NAV (price of one unit)", b.nav(), Units.INR_PRICE, b.source(), b.navDate(), cmp, "nav");
    }

    /** Views for the given entities (one bundle call for all of them). sampleData is true if the bundle says so. */
    private Listed views(List<WatchlistItemEntity> entities) {
        List<String> stockIds = new ArrayList<>();
        List<String> fundIds = new ArrayList<>();
        for (WatchlistItemEntity e : entities) (e.getKind() == Kind.STOCK ? stockIds : fundIds).add(e.getInstrumentId());
        Map<String, BundleStock> stocks = new LinkedHashMap<>();
        Map<String, BundleFund> funds = new LinkedHashMap<>();
        boolean sample = false;
        if (!entities.isEmpty()) {
            BundleResponse b = portfolio.bundle(stockIds, fundIds);
            sample = b.sampleData();
            if (b.stocks() != null) for (BundleStock s : b.stocks()) stocks.put(s.symbol(), s);
            if (b.funds() != null) for (BundleFund f : b.funds()) funds.put(f.schemeCode(), f);
        }
        List<WatchlistItem> items = new ArrayList<>();
        for (WatchlistItemEntity e : entities) {
            items.add(new WatchlistItem(e.getId(), e.getKind().name(), e.getInstrumentId(), e.getName(), e.getSubtitle(),
                    e.getNote() == null ? "" : e.getNote(), Times.iso(e.getCreatedAt()), Times.iso(e.getUpdatedAt()),
                    latest(e, stocks, funds), checkPath(e)));
        }
        return new Listed(sample, items);
    }

    public Listed list() { return views(repo.findAllByOrderByCreatedAtDescIdDesc()); }

    /** Newest five, for the home page. */
    public List<WatchlistItem> newestFive() { return views(repo.findTop5ByOrderByCreatedAtDescIdDesc()).items(); }

    private static String checkNote(String note) {
        String n = note == null ? "" : note;
        if (n.length() > MAX_NOTE) throw ApiException.badRequest("The note can be at most 1000 characters.");
        return n;
    }

    private static WatchlistItemResponse withSample(boolean sample, WatchlistItem i) {
        return new WatchlistItemResponse(sample, i.id(), i.kind(), i.instrumentId(), i.name(), i.subtitle(), i.note(),
                i.createdAt(), i.updatedAt(), i.latest(), i.checkPath());
    }

    public Saved add(String kindText, String instrumentId, String note) {
        Kind kind = Instruments.parseKind(kindText);
        String id = Instruments.normalize(kind, instrumentId);
        String n = checkNote(note);
        Resolved r = portfolio.resolve(kind, id);
        OffsetDateTime now = Times.now();
        Optional<WatchlistItemEntity> existing = repo.findByKindAndInstrumentId(kind, id);
        boolean created = existing.isEmpty();
        WatchlistItemEntity e = existing.orElseGet(WatchlistItemEntity::new);
        if (created) {
            e.setKind(kind);
            e.setInstrumentId(id);
            e.setCreatedAt(now);
        }
        e.setName(r.name());
        e.setSubtitle(r.subtitle());
        e.setNote(n);
        e.setUpdatedAt(now);
        WatchlistItemEntity saved = repo.save(e);
        Listed l = views(List.of(saved));
        return new Saved(withSample(l.sampleData() || r.sampleData(), l.items().get(0)), created);
    }

    public WatchlistItemResponse patch(long id, String note) {
        WatchlistItemEntity e = repo.findById(id)
                .orElseThrow(() -> ApiException.notFound("No watchlist item with id " + id + ".", Map.of("id", id)));
        e.setNote(checkNote(note));
        e.setUpdatedAt(Times.now());
        WatchlistItemEntity saved = repo.save(e);
        Listed l = views(List.of(saved));
        return withSample(l.sampleData(), l.items().get(0));
    }

    public void delete(long id) {
        if (!repo.existsById(id)) {
            throw ApiException.notFound("No watchlist item with id " + id + ".", Map.of("id", id));
        }
        repo.deleteById(id);
    }
}
