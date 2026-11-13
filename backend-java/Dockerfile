# Build stage: Maven + JDK 21. Run stage: JRE 21 only.
FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /build
COPY pom.xml .
RUN mvn -q -B dependency:go-offline
COPY src ./src
RUN mvn -q -B -DskipTests package

FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /build/target/backend-java.jar /app/backend-java.jar
# H2 database files live here; mount a volume (STORAGE_H2PATH=/data/stockanalyzer).
VOLUME /data
EXPOSE 8080
# Configuration comes from the shared YAML (APP_CONFIG) and relaxed-binding env vars such as SERVICES_PYTHONBASEURL.
ENTRYPOINT ["java", "-jar", "/app/backend-java.jar"]
