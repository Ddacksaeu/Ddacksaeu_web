import { Link, createFileRoute, useNavigate } from "@tanstack/react-router";
import { FormEvent, useState } from "react";
import { login } from "../lib/api/auth";
import { saveSession } from "../lib/auth";

export const Route = createFileRoute("/login")({ component: LoginPage });

function LoginPage() {
  const navigate = useNavigate();
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError("");
    const data = new FormData(event.currentTarget);
    try { saveSession(await login(String(data.get("email")), String(data.get("password")))); await navigate({ to: "/" }); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "로그인에 실패했습니다."); }
  }
  return <main className="grid min-h-screen place-items-center bg-[color:var(--surface)] p-4"><form onSubmit={submit} className="w-full max-w-sm space-y-4 rounded-2xl border bg-white p-7 shadow-sm"><h1 className="text-2xl font-bold">로그인</h1><p className="text-sm text-muted-foreground">내 CV와 관심 연구실을 안전하게 관리하세요.</p><input name="email" type="email" required placeholder="이메일" className="w-full rounded-md border p-3" /><input name="password" type="password" required placeholder="비밀번호" className="w-full rounded-md border p-3" />{error && <p className="text-sm text-destructive">{error}</p>}<button className="w-full rounded-md bg-primary p-3 font-medium text-primary-foreground">로그인</button><p className="text-center text-sm">계정이 없으신가요? <Link to="/signup" className="text-primary underline">회원가입</Link></p></form></main>;
}
