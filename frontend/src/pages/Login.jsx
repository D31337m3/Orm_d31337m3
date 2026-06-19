import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { Terminal } from "lucide-react";

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      const u = await login(email, password);
      nav(u.is_admin ? "/admin" : "/dashboard");
    } catch (e) {
      setError(e.response?.data?.detail || "Login failed");
    } finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen bg-[#050505] flex items-center justify-center px-4">
      <div className="w-full max-w-md brutal-card p-10">
        <Link to="/" className="flex items-center gap-2 mb-8" data-testid="auth-logo">
          <Terminal className="text-[#FF3333]" size={20} />
          <span className="font-display font-black text-xl">d31337m3</span>
        </Link>
        <div className="overline mb-2">// authenticate</div>
        <h1 className="font-display font-black text-3xl mb-8">Sign in.</h1>
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <div className="overline mb-1">email</div>
            <input data-testid="login-email" type="email" required value={email} onChange={(e)=>setEmail(e.target.value)} className="brutal-input" />
          </div>
          <div>
            <div className="overline mb-1">password</div>
            <input data-testid="login-password" type="password" required value={password} onChange={(e)=>setPassword(e.target.value)} className="brutal-input" />
          </div>
          {error && <div data-testid="login-error" className="font-mono text-xs text-[#FF3333] py-2">› {error}</div>}
          <button data-testid="login-submit" type="submit" disabled={loading} className="brutal-btn brutal-btn-primary w-full">
            {loading ? "Authenticating..." : "Sign In"}
          </button>
        </form>
        <div className="mt-6 text-center font-mono text-xs text-zinc-500">
          New here? <Link to="/register" data-testid="goto-register" className="text-white hover:text-[#FF3333]">create an account →</Link>
        </div>
      </div>
    </div>
  );
}
