# CSRF 문제 해결 요청

> **문제**: AI Backend → Spring Backend Callback 요청 시 CSRF 검증 실패  
> **작성일**: 2026-01-07

---

## 1. 현상

```
403 Forbidden
{"success":false,"error":"CSRF validation failed","message":"Invalid origin"}
```

- **발생 위치**: `/api/internal/ai/analysis/callback`
- **요청 출처**: FastAPI (AI Backend) → Spring (Main Backend)
- **상황**: AI 분석 완료 후 결과를 Spring에 전달하는 Callback 요청이 거부됨

---

## 2. 원인 분석

### CSRF (Cross-Site Request Forgery) 란?
- 브라우저에서 악성 사이트가 사용자의 세션 쿠키를 이용해 요청을 보내는 공격
- **방어 방법**: `Origin` 헤더 검증, CSRF 토큰 검증

### 현재 상황
```
[FastAPI Container] --HTTP POST--> [Spring Container]
                    (Origin 헤더 없음)
```

- FastAPI는 **브라우저가 아님** → `Origin` 헤더가 없음
- Spring Security는 `Origin` 헤더가 없거나 허용되지 않으면 CSRF 검증 실패 처리

### 왜 CSRF 보호가 불필요한가?
| 조건 | 브라우저 요청 | 서버 간 요청 (현재) |
|------|---------------|---------------------|
| 세션 쿠키 사용 | ✅ 사용 | ❌ 미사용 |
| 사용자 인증 상태 | ✅ 로그인 상태 | ❌ 해당 없음 |
| CSRF 공격 가능성 | ⚠️ 있음 | ❌ 없음 |
| CSRF 보호 필요 | ✅ 필요 | ❌ **불필요** |

---

## 3. 해결 방안

### Option A: 내부 API에 CSRF 비활성화 (권장)

```java
// SecurityConfig.java

@Bean
public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
    http
        // ... 다른 설정들 ...
        .csrf(csrf -> csrf
            // 내부 API는 서버 간 통신이므로 CSRF 검사 제외
            .ignoringRequestMatchers("/api/internal/**")
        );
    return http.build();
}
```

**장점**:
- 근본적인 해결
- 내부 API만 제외하므로 사용자 API는 여전히 보호됨
- FastAPI 코드 수정 불필요

---

### Option B: CorsFilter에서 Origin 허용 (차선책)

```java
// CorsConfig.java 또는 SecurityConfig.java

@Bean
public CorsFilter corsFilter() {
    CorsConfiguration config = new CorsConfiguration();
    config.addAllowedOrigin("http://stolink-ai-backend:8000");  // AI Backend Origin
    config.addAllowedOrigin("http://localhost:8000");           // 로컬 테스트용
    config.addAllowedMethod("*");
    config.addAllowedHeader("*");
    
    UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
    source.registerCorsConfiguration("/api/internal/**", config);
    
    return new CorsFilter(source);
}
```

**단점**: FastAPI에서 `Origin` 헤더를 수동으로 설정해야 함

---

### Option C: IP 기반 화이트리스트 (가장 안전)

```java
// InternalApiSecurityFilter.java

@Component
public class InternalApiSecurityFilter extends OncePerRequestFilter {
    
    private static final Set<String> ALLOWED_IPS = Set.of(
        "172.18.0.0/16",  // Docker 내부 네트워크
        "10.0.0.0/8",     // Private network
        "127.0.0.1"       // Localhost
    );
    
    @Override
    protected void doFilterInternal(HttpServletRequest request, 
                                    HttpServletResponse response,
                                    FilterChain chain) {
        if (request.getRequestURI().startsWith("/api/internal/")) {
            String clientIp = request.getRemoteAddr();
            if (!isAllowedIp(clientIp)) {
                response.sendError(403, "IP not allowed");
                return;
            }
        }
        chain.doFilter(request, response);
    }
}
```

**장점**: CSRF와 무관하게 IP로 접근 제어

---

## 4. 권장 사항

### 즉시 적용: Option A
```java
.csrf(csrf -> csrf.ignoringRequestMatchers("/api/internal/**"))
```

### 장기 적용: Option A + Option C 조합
- CSRF 비활성화 + IP 화이트리스트로 이중 보호

---

## 5. 추가 고려사항

### 현재 Event Sourcing 아키텍처 전환 중
- Callback 대신 RabbitMQ 이벤트 발행 방식으로 전환 진행 중
- 전환 완료 시 HTTP Callback 제거 예정
- **단기 Workaround로 Option A 적용 권장**

### 영향받는 엔드포인트
```
POST /api/internal/ai/analysis/callback
POST /api/internal/ai/jobs/{jobId}/status
PATCH /api/documents/{documentId}/analysis-status
```

---

## 6. 참고 자료

- [Spring Security CSRF Protection](https://docs.spring.io/spring-security/reference/servlet/exploits/csrf.html)
- [When to disable CSRF](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html#when-to-use-csrf-protection)
