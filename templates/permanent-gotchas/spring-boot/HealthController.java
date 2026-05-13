package PACKAGE_PLACEHOLDER;

import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

// Substitute PACKAGE_PLACEHOLDER with the project's actual base package
// (e.g., com.example.apinew). The plugin's smoke gate hits /health, but
// Spring Boot's actuator exposes /actuator/health — explicit controller
// bridges that gap.
@RestController
public class HealthController {

    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("status", "UP");
    }
}
