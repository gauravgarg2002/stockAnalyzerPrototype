package com.stockanalyzer.service;

import com.stockanalyzer.config.AppProperties;
import com.stockanalyzer.python.PythonClient;
import com.stockanalyzer.python.dto.PyDto.Health;
import com.stockanalyzer.web.dto.ConnectDto.MetaResponse;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.stereotype.Service;

/** A.1: adapter modes and the sample-data flag from Python's health, plus config values. */
@Service
public class MetaService {

    private final PythonClient python;
    private final AppProperties props;

    public MetaService(PythonClient python, AppProperties props) {
        this.python = python;
        this.props = props;
    }

    public MetaResponse meta() {
        Health h = python.health();
        Map<String, String> adapters = h.adapters() == null ? new LinkedHashMap<>() : h.adapters();
        return new MetaResponse(h.sampleData(), h.asOf(), adapters, h.llmEnabled(), props.app().disclaimer(),
                props.app().defaultIllustrativeAmountInr());
    }
}
