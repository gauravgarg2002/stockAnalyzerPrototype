package com.stockanalyzer.web;

import com.stockanalyzer.service.ImportService;
import com.stockanalyzer.web.dto.ConnectDto.ImportResult;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

/** Import from the broker or from a CAMS/KFintech statement PDF (contract A.13). */
@RestController
@RequestMapping("/api/import")
public class ImportController {

    private final ImportService service;

    public ImportController(ImportService service) { this.service = service; }

    @PostMapping("/kite")
    public ImportResult importKite() { return service.importFromBroker(); }

    @PostMapping(value = "/statement", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ImportResult importStatement(@RequestParam("file") MultipartFile file,
                                        @RequestParam(name = "password", required = false) String password) {
        return service.importFromStatement(file, password);
    }
}
