import api from "@/lib/api";

// 🔹 LOGIN
export async function loginUser(email: string, password: string) {
  const formData = new URLSearchParams();
  formData.append("username", email); // backend username=email bekliyor
  formData.append("password", password);

  const res = await api.post("/auth/login", formData, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  return res.data; // { access_token, token_type }
}

// 🔹 REGISTER
export async function registerUser(firstName: string, lastName: string, email: string, password: string) {
  const res = await api.post("/auth/register", {
    first_name: firstName,
    last_name: lastName,
    email,
    password,
  });
  return res.data; // user objesi
}

// 🔹 ME
export async function getCurrentUser() {
  const res = await api.get("/auth/me");
  return res.data;
}
