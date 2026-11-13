package com.stockanalyzer.service;

import com.stockanalyzer.config.AppProperties;
import com.stockanalyzer.domain.HoldingRepository;
import com.stockanalyzer.domain.HoldingSource;
import com.stockanalyzer.domain.ImportLogEntity;
import com.stockanalyzer.domain.ImportLogRepository;
import com.stockanalyzer.engine.model.Kind;
import com.stockanalyzer.python.PythonClient;
import com.stockanalyzer.python.dto.PyDto.BrokerStatus;
import com.stockanalyzer.web.ApiException;
import com.stockanalyzer.web.dto.ConnectDto.ConnectionResponse;
import com.stockanalyzer.web.dto.ConnectDto.HoldingsSummary;
import com.stockanalyzer.web.dto.ConnectDto.StartResponse;
import com.stockanalyzer.web.dto.ConnectDto.StatusResponse;
import com.stockanalyzer.web.dto.Shared.ImportLogEntry;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

/** Broker login flow (session state lives in Python) and the connection summary for the Connect page. */
@Service
public class ConnectService {

    private static final Logger LOG = LoggerFactory.getLogger(ConnectService.class);

    private final PythonClient python;
    private final AppProperties props;
    private final HoldingRepository holdingRepo;
    private final ImportLogRepository logRepo;

    /** The login URL from the last start call, shown again while the login is pending. */
    private volatile String lastLoginUrl;

    public ConnectService(PythonClient python, AppProperties props, HoldingRepository holdingRepo,
                          ImportLogRepository logRepo) {
        this.python = python;
        this.props = props;
        this.holdingRepo = holdingRepo;
        this.logRepo = logRepo;
    }

    private String mode(BrokerStatus s) {
        return s.brokerMode() != null ? s.brokerMode() : props.adapters().broker();
    }

    public ConnectionResponse connection() {
        BrokerStatus s = python.brokerLoginStatus();
        List<ImportLogEntry> imports = new ArrayList<>();
        for (ImportLogEntity e : logRepo.findTop10ByOrderByIdDesc()) imports.add(ImportService.toDto(e));
        Map<String, Integer> bySource = new LinkedHashMap<>();
        for (HoldingSource src : HoldingSource.values()) bySource.put(src.name(), (int) holdingRepo.countBySource(src));
        boolean sample = s.sampleData() || imports.stream().anyMatch(ImportLogEntry::sampleData);
        String loginUrl = "PENDING_LOGIN".equals(s.status()) ? (s.loginUrl() != null ? s.loginUrl() : lastLoginUrl) : null;
        return new ConnectionResponse(sample, mode(s), s.status(), s.accountLabel(), loginUrl,
                imports.isEmpty() ? null : imports.get(0).finishedAt(), imports,
                new HoldingsSummary((int) holdingRepo.countByKind(Kind.STOCK), (int) holdingRepo.countByKind(Kind.FUND), bySource));
    }

    public StartResponse start() {
        BrokerStatus s = python.brokerLoginStart();
        lastLoginUrl = s.loginUrl();
        return new StartResponse(s.sampleData(), mode(s), s.status(), s.loginUrl(), s.message());
    }

    public StatusResponse status() {
        BrokerStatus s = python.brokerLoginStatus();
        return new StatusResponse(s.sampleData(), mode(s), s.status(), s.accountLabel(), s.message());
    }

    public StartResponse disconnect() {
        BrokerStatus s = python.brokerLogout();
        lastLoginUrl = null;
        return new StartResponse(s.sampleData(), mode(s), s.status(), null, s.message());
    }

    /**
     * Kite Connect redirect. Returns the frontend URL to send the browser to: /connect?kite=connected, or
     * ?kite=failed when the login did not succeed or the token exchange failed.
     */
    public String completeLogin(String requestToken, String status) {
        String base = props.services().frontendBaseUrl();
        if (base.endsWith("/")) base = base.substring(0, base.length() - 1);
        boolean ok = false;
        if ("success".equalsIgnoreCase(status) && requestToken != null && !requestToken.isBlank()) {
            try {
                BrokerStatus s = python.brokerLoginComplete(requestToken);
                ok = "CONNECTED".equals(s.status());
            } catch (ApiException e) {
                LOG.warn("Kite login could not be completed: {} {}", e.code(), e.getMessage());
            }
        }
        return base + "/connect?kite=" + (ok ? "connected" : "failed");
    }
}
