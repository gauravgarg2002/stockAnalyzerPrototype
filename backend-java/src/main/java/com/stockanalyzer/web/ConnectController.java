package com.stockanalyzer.web;

import com.stockanalyzer.service.ConnectService;
import com.stockanalyzer.web.dto.ConnectDto.ConnectionResponse;
import com.stockanalyzer.web.dto.ConnectDto.StartResponse;
import com.stockanalyzer.web.dto.ConnectDto.StatusResponse;
import java.net.URI;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/** Connection summary and the Kite login flow (contract A.12). */
@RestController
@RequestMapping("/api")
public class ConnectController {

    private final ConnectService service;

    public ConnectController(ConnectService service) { this.service = service; }

    @GetMapping("/connection")
    public ConnectionResponse connection() { return service.connection(); }

    @PostMapping("/connect/kite/start")
    public StartResponse start() { return service.start(); }

    @GetMapping("/connect/kite/status")
    public StatusResponse status() { return service.status(); }

    @PostMapping("/connect/kite/disconnect")
    public StartResponse disconnect() { return service.disconnect(); }

    /**
     * Login redirect target (kite.redirectUrl). Kite Connect sends request_token + status=success; the hosted Kite
     * MCP server's OAuth sends code + state (or error). Answers 302 to the frontend connect page.
     */
    @GetMapping("/connect/kite/callback")
    public ResponseEntity<Void> callback(@RequestParam(name = "request_token", required = false) String requestToken,
                                         @RequestParam(name = "code", required = false) String code,
                                         @RequestParam(name = "state", required = false) String state,
                                         @RequestParam(name = "error", required = false) String error,
                                         @RequestParam(name = "action", required = false) String action,
                                         @RequestParam(name = "status", required = false) String status) {
        String token = requestToken != null ? requestToken : code;
        String outcome = error != null ? "error" : (status != null ? status : (code != null ? "success" : null));
        String target = service.completeLogin(token, state, outcome);
        return ResponseEntity.status(HttpStatus.FOUND).location(URI.create(target)).build();
    }
}
