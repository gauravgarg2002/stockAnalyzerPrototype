package com.stockanalyzer.web;

import static org.hamcrest.Matchers.containsString;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.stockanalyzer.service.PortfolioService;
import com.stockanalyzer.web.dto.PortfolioDto.PortfolioResponse;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.test.web.servlet.MockMvc;

/** Web layer only: JSON shape (nulls present) and the contract error shape. Needs the Spring test libraries. */
@WebMvcTest(PortfolioController.class)
@Import(ApiExceptionHandler.class)
class PortfolioControllerTest {

    @Autowired
    private MockMvc mvc;

    @MockBean
    private PortfolioService service;

    @Test
    void portfolioIsServedWithCamelCaseKeysAndNullsPresent() throws Exception {
        PortfolioResponse empty = new PortfolioResponse(true, "2026-10-30", false, false, null, List.of(), List.of(),
                null, null, null, null, null, null, List.of());
        when(service.portfolio()).thenReturn(empty);

        mvc.perform(get("/api/portfolio"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.sampleData").value(true))
                .andExpect(jsonPath("$.asOf").value("2026-10-30"))
                .andExpect(jsonPath("$.hasHoldings").value(false))
                .andExpect(jsonPath("$.holdings").isArray())
                .andExpect(content().string(containsString("\"totals\":null")))
                .andExpect(content().string(containsString("\"exposure\":null")));
    }

    @Test
    void pythonUnreachableBecomesUpstreamUnavailable() throws Exception {
        when(service.portfolio()).thenThrow(ApiException.upstreamUnavailable("The data service did not answer."));

        mvc.perform(get("/api/portfolio"))
                .andExpect(status().isBadGateway())
                .andExpect(jsonPath("$.error.code").value("UPSTREAM_UNAVAILABLE"))
                .andExpect(jsonPath("$.error.message").value("The data service did not answer."))
                .andExpect(content().string(containsString("\"details\":null")));
    }

    @Test
    void pythonErrorsAreReEmittedWithTheSameStatusAndDetails() throws Exception {
        when(service.portfolio()).thenThrow(
                ApiException.notFound("No stock found for symbol XYZ.", Map.of("symbol", "XYZ")));

        mvc.perform(get("/api/portfolio"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error.code").value("NOT_FOUND"))
                .andExpect(jsonPath("$.error.details.symbol").value("XYZ"));
    }

    @Test
    void unexpectedFailuresAreInternalErrorsWithoutLeakingDetails() throws Exception {
        when(service.portfolio()).thenThrow(new IllegalStateException("secret internals"));

        mvc.perform(get("/api/portfolio"))
                .andExpect(status().isInternalServerError())
                .andExpect(jsonPath("$.error.code").value("INTERNAL"))
                .andExpect(content().string(org.hamcrest.Matchers.not(containsString("secret internals"))));
    }
}
