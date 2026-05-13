package PACKAGE_PLACEHOLDER;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

// Substitute PACKAGE_PLACEHOLDER with the project's actual base package.
// Spring Boot rejects cross-origin requests by default. Allow the standard
// UI dev ports for local work; tighten via application-production.yml or
// an environment-conditional bean before any non-local deploy.
@Configuration
public class CorsConfig implements WebMvcConfigurer {

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/**")
                .allowedOrigins(
                        "http://localhost:5173",
                        "http://localhost:3000",
                        "http://localhost:4200"
                )
                .allowedMethods("*")
                .allowedHeaders("*")
                .allowCredentials(true);
    }
}
