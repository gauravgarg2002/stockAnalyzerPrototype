package com.stockanalyzer.web;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.stockanalyzer.config.AppProperties;
import com.stockanalyzer.domain.HoldingRepository;
import com.stockanalyzer.domain.ImportLogRepository;
import com.stockanalyzer.python.PythonClient;
import com.stockanalyzer.python.dto.PyDto.BrokerStatus;
import com.stockanalyzer.service.ConnectService;
import com.stockanalyzer.web.dto.ConnectDto.StartResponse;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.test.web.servlet.MockMvc;

/** The Kite login endpoints and the redirect callback. Needs the Spring test libraries. */
@WebMvcTest(ConnectController.class)
@Import(ApiExceptionHandler.class)
class ConnectControllerTest {

    @Autowired
    private MockMvc mvc;

    @MockBean
    private ConnectService service;

    @Test
    void startReturnsThePendingLoginUrl() throws Exception {
        when(service.start()).thenReturn(new StartResponse(false, "kite_connect", "PENDING_LOGIN",
                "https://kite.zerodha.com/connect/login?v=3&api_key=abc", "Waiting for you to finish logging in to Kite."));

        mvc.perform(post("/api/connect/kite/start"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.brokerMode").value("kite_connect"))
                .andExpect(jsonPath("$.status").value("PENDING_LOGIN"))
                .andExpect(jsonPath("$.loginUrl").value("https://kite.zerodha.com/connect/login?v=3&api_key=abc"));
    }

    @Test
    void callbackRedirectsToTheFrontendConnectPage() throws Exception {
        when(service.completeLogin("tok123", "success")).thenReturn("http://localhost:5173/connect?kite=connected");

        mvc.perform(get("/api/connect/kite/callback")
                        .param("request_token", "tok123").param("action", "login").param("status", "success"))
                .andExpect(status().isFound())
                .andExpect(header().string("Location", "http://localhost:5173/connect?kite=connected"));
    }

    @Test
    void callbackWithoutParametersStillRedirects() throws Exception {
        when(service.completeLogin(null, null)).thenReturn("http://localhost:5173/connect?kite=failed");

        mvc.perform(get("/api/connect/kite/callback"))
                .andExpect(status().isFound())
                .andExpect(header().string("Location", "http://localhost:5173/connect?kite=failed"));
    }

    @Test
    void brokerNotConnectedUsesTheContractErrorShape() throws Exception {
        when(service.status()).thenThrow(ApiException.brokerNotConnected("Connect your Zerodha account first."));

        mvc.perform(get("/api/connect/kite/status"))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.error.code").value("BROKER_NOT_CONNECTED"));
    }

    // ---- ConnectService.completeLogin, plain unit tests (no Spring context needed) ----------------------------

    private static ConnectService serviceWith(PythonClient python) {
        AppProperties props = new AppProperties(
                new AppProperties.App("2026-10-30", 100000, "Information only, not investment advice."),
                null,
                new AppProperties.Services("http://localhost:8000", "http://localhost:5173/"),
                new AppProperties.Adapters("kite_connect", "mock", "mock", "mock", "mock", "mock", "mock", "auto"),
                null, null, null, null);
        return new ConnectService(python, props, mock(HoldingRepository.class), mock(ImportLogRepository.class));
    }

    @Test
    void completeLoginReportsConnectedWhenPythonSaysConnected() {
        PythonClient python = mock(PythonClient.class);
        when(python.brokerLoginComplete("tok")).thenReturn(
                new BrokerStatus(false, "kite_connect", "CONNECTED", null, "Your Zerodha account (AB1234)", "Connected."));

        String url = serviceWith(python).completeLogin("tok", "success");

        assertEquals("http://localhost:5173/connect?kite=connected", url);
    }

    @Test
    void completeLoginFailsWithoutCallingPythonWhenKiteSaidNoSuccess() {
        PythonClient python = mock(PythonClient.class);

        String url = serviceWith(python).completeLogin("tok", "error");

        assertEquals("http://localhost:5173/connect?kite=failed", url);
        verify(python, never()).brokerLoginComplete(anyString());
    }

    @Test
    void completeLoginFailsWhenPythonRaisesAnError() {
        PythonClient python = mock(PythonClient.class);
        when(python.brokerLoginComplete("tok")).thenThrow(
                new ApiException(400, "BAD_REQUEST", "Only available with kite_connect.", null));

        String url = serviceWith(python).completeLogin("tok", "success");

        assertEquals("http://localhost:5173/connect?kite=failed", url);
    }
}
