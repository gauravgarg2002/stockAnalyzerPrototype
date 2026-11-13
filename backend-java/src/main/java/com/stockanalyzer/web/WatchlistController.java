package com.stockanalyzer.web;

import com.stockanalyzer.service.WatchlistService;
import com.stockanalyzer.service.WatchlistService.Listed;
import com.stockanalyzer.service.WatchlistService.Saved;
import com.stockanalyzer.web.dto.ConnectDto.WatchlistCreateRequest;
import com.stockanalyzer.web.dto.ConnectDto.WatchlistPatchRequest;
import com.stockanalyzer.web.dto.ConnectDto.WatchlistResponse;
import com.stockanalyzer.web.dto.Shared.WatchlistItemResponse;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/watchlist")
public class WatchlistController {

    private final WatchlistService service;

    public WatchlistController(WatchlistService service) { this.service = service; }

    @GetMapping
    public WatchlistResponse list() {
        Listed l = service.list();
        return new WatchlistResponse(l.sampleData(), l.items());
    }

    @PostMapping
    public ResponseEntity<WatchlistItemResponse> add(@RequestBody WatchlistCreateRequest request) {
        if (request == null) throw ApiException.badRequest("A request body is required.");
        Saved saved = service.add(request.kind(), request.instrumentId(), request.note());
        return ResponseEntity.status(saved.created() ? HttpStatus.CREATED : HttpStatus.OK).body(saved.item());
    }

    @PatchMapping("/{id}")
    public WatchlistItemResponse patch(@PathVariable("id") long id, @RequestBody WatchlistPatchRequest request) {
        if (request == null) throw ApiException.badRequest("A request body is required.");
        return service.patch(id, request.note());
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable("id") long id) {
        service.delete(id);
        return ResponseEntity.noContent().build();
    }
}
