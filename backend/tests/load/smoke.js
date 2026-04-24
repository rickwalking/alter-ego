import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  thresholds: {
    http_req_duration: ['p(99)<3000'],
    http_req_failed: ['rate<0.01'],
    checks: ['rate==1.0'],
  },
  stages: [
    { duration: '10s', target: 5 },
    { duration: '20s', target: 5 },
    { duration: '10s', target: 0 },
  ],
};

const BASE_URL = __ENV.API_BASE_URL || 'http://localhost:8000';

export default function () {
  // Health check
  const healthRes = http.get(`${BASE_URL}/health`);
  check(healthRes, {
    'health status is 200': (r) => r.status === 200,
    'health response is healthy': (r) => r.json('status') === 'healthy',
  });

  // Ready check
  const readyRes = http.get(`${BASE_URL}/health/ready`);
  check(readyRes, {
    'ready status is 200': (r) => r.status === 200,
  });

  // Auth token exchange (setup endpoint)
  const tokenRes = http.post(`${BASE_URL}/api/auth/token`, JSON.stringify({
    api_key: 'test-api-key',
  }), {
    headers: { 'Content-Type': 'application/json' },
  });
  check(tokenRes, {
    'token exchange returns 200 or 401': (r) => r.status === 200 || r.status === 401,
  });

  // List documents
  const docsRes = http.get(`${BASE_URL}/api/documents?limit=5`);
  check(docsRes, {
    'documents list returns 200 or 401': (r) => r.status === 200 || r.status === 401,
  });

  // Search
  const searchRes = http.get(`${BASE_URL}/api/search?query=test&top_k=3`);
  check(searchRes, {
    'search returns 200 or 401': (r) => r.status === 200 || r.status === 401,
  });

  sleep(1);
}
