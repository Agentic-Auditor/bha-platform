const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000";

async function request(path, options = {}) {
  const res = await fetch(`${API_URL}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Request failed");
  return data;
}

export function createAssessment(businessType, context = {}) {
  return request("/api/v1/assessments", {
    method: "POST",
    body: JSON.stringify({ business_type: businessType, ...context }),
  });
}

export function captureLead(id, name, email) {
  return request(`/api/v1/assessments/${id}/lead`, {
    method: "PATCH",
    body: JSON.stringify({ name, email }),
  });
}

export function getAssessment(id) {
  return request(`/api/v1/assessments/${id}`);
}

export function submitAnswer(id, questionId, score) {
  return request(`/api/v1/assessments/${id}/answers`, {
    method: "POST",
    body: JSON.stringify({ question_id: questionId, score }),
  });
}

export function calculateScore(id) {
  return request(`/api/v1/assessments/${id}/calculate`, { method: "POST" });
}

export function getFreeResults(id) {
  return request(`/api/v1/assessments/${id}/results/free`);
}

export function getFullResults(id) {
  return request(`/api/v1/assessments/${id}/results/full`);
}

export function uploadSlip(id, file) {
  const formData = new FormData();
  formData.append("slip", file);
  return fetch(`${API_URL}/api/v1/assessments/${id}/payments`, {
    method: "POST",
    credentials: "include",
    body: formData,
  }).then(async (res) => {
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Upload failed");
    return data;
  });
}

export function getPaymentStatus(id, paymentId) {
  return request(`/api/v1/assessments/${id}/payments/${paymentId}`);
}

// ── Membership / User API ────────────────────────────────────────────────────

export function userLogin(email, name = "") {
  return request("/api/v1/users/login", {
    method: "POST",
    body: JSON.stringify({ email, name }),
  });
}

export function userLogout() {
  return request("/api/v1/users/logout", { method: "POST" });
}

export function getMe() {
  return request("/api/v1/users/me");
}

export function getTrend() {
  return request("/api/v1/users/trend");
}

export function getAlerts() {
  return request("/api/v1/users/alerts");
}

export function getMembershipPaymentStatus() {
  return request("/api/v1/membership/payment/status");
}

export function uploadMembershipSlip(file) {
  const formData = new FormData();
  formData.append("slip", file);
  return fetch(`${API_URL}/api/v1/membership/payment`, {
    method: "POST",
    credentials: "include",
    body: formData,
  }).then(async (res) => {
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Upload failed");
    return data;
  });
}

export function downloadPdf(id) {
  return fetch(`${API_URL}/api/v1/assessments/${id}/results/pdf`, {
    credentials: "include",
  }).then(async (res) => {
    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.error || "Download failed");
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `BHA_Report.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  });
}
