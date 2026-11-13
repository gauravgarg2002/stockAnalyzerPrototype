package com.stockanalyzer.service;

import com.stockanalyzer.domain.HoldingEntity;
import com.stockanalyzer.domain.HoldingRepository;
import com.stockanalyzer.domain.HoldingSource;
import com.stockanalyzer.engine.model.Kind;
import com.stockanalyzer.service.PortfolioService.Resolved;
import com.stockanalyzer.web.ApiException;
import com.stockanalyzer.web.dto.ConnectDto.HoldingCreated;
import com.stockanalyzer.web.dto.ConnectDto.HoldingView;
import com.stockanalyzer.web.dto.ConnectDto.HoldingsResponse;
import com.stockanalyzer.web.dto.ConnectDto.ManualHoldingRequest;
import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Service;

/** List, manually add and delete holdings (contract A.13). */
@Service
public class HoldingsService {

    private final HoldingRepository repo;
    private final PortfolioService portfolio;
    private final ResponseCache cache;

    public HoldingsService(HoldingRepository repo, PortfolioService portfolio, ResponseCache cache) {
        this.repo = repo;
        this.portfolio = portfolio;
        this.cache = cache;
    }

    static HoldingView toView(HoldingEntity h) {
        return new HoldingView(h.getId(), h.getKind().name(), h.getInstrumentId(), h.getName(), h.getQuantity(),
                h.getAvgPrice(), h.getFirstBuyDate() == null ? null : h.getFirstBuyDate().toString(),
                h.getSource().name(), Times.iso(h.getImportedAt()));
    }

    public HoldingsResponse list() {
        List<HoldingView> views = new ArrayList<>();
        boolean sample = false;
        for (HoldingEntity h : repo.findAllByOrderByIdAsc()) {
            views.add(toView(h));
            sample |= h.isSampleData();
        }
        return new HoldingsResponse(sample, views);
    }

    public HoldingCreated add(ManualHoldingRequest req) {
        if (req == null) throw ApiException.badRequest("A request body is required.");
        Kind kind = Instruments.parseKind(req.kind());
        String id = Instruments.normalize(kind, req.instrumentId());
        if (req.quantity() == null || !(req.quantity() > 0) || req.quantity() > 1e12) {
            throw ApiException.badRequest("quantity must be more than 0.");
        }
        if (req.avgPrice() == null || !(req.avgPrice() > 0) || req.avgPrice() > 1e12) {
            throw ApiException.badRequest("avgPrice must be more than 0.");
        }
        LocalDate buy = null;
        if (req.firstBuyDate() != null && !req.firstBuyDate().isBlank()) {
            try {
                buy = LocalDate.parse(req.firstBuyDate().trim());
            } catch (DateTimeParseException e) {
                throw ApiException.badRequest("firstBuyDate must look like 2025-01-15.");
            }
        }
        Resolved r = portfolio.resolve(kind, id);
        HoldingEntity h = new HoldingEntity();
        h.setKind(kind);
        h.setInstrumentId(id);
        h.setName(r.name());
        h.setQuantity(req.quantity());
        h.setAvgPrice(req.avgPrice());
        h.setFirstBuyDate(buy);
        h.setSource(HoldingSource.MANUAL);
        h.setSampleData(r.sampleData());
        h.setImportedAt(Times.now());
        HoldingEntity saved = repo.save(h);
        cache.clearAll();
        return new HoldingCreated(r.sampleData(), saved.getId(), kind.name(), id, saved.getName(), saved.getQuantity(),
                saved.getAvgPrice(), buy == null ? null : buy.toString(), HoldingSource.MANUAL.name(),
                Times.iso(saved.getImportedAt()));
    }

    public void delete(long id) {
        if (!repo.existsById(id)) {
            throw ApiException.notFound("No holding with id " + id + ".", Map.of("id", id));
        }
        repo.deleteById(id);
        cache.clearAll();
    }
}
