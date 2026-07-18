import { Link, createFileRoute, useNavigate } from "@tanstack/react-router";
import { FormEvent, useState } from "react";
import { signup } from "../lib/api/auth";
import { saveSession } from "../lib/auth";

export const Route = createFileRoute("/signup")({ component: SignupPage });

function SignupPage() {
  const navigate = useNavigate();
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); const data = new FormData(event.currentTarget);
    const password = String(data.get("password"));
    if (password !== String(data.get("passwordConfirmation"))) { setError("비밀번호 확인이 일치하지 않습니다."); return; }
    try { saveSession(await signup(String(data.get("email")), password, String(data.get("name")))); await navigate({ to: "/" }); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "회원가입에 실패했습니다."); }
  }
  return <main className="grid min-h-screen place-items-center bg-[color:var(--surface)] p-4"><form onSubmit={submit} className="w-full max-w-sm space-y-4 rounded-2xl border bg-white p-7 shadow-sm"><h1 className="text-2xl font-bold">회원가입</h1><p className="text-sm text-muted-foreground">이메일 형식만 검증하며, 인증 메일은 보내지 않습니다.</p><input name="name" required minLength={2} placeholder="이름 또는 닉네임" className="w-full rounded-md border p-3" /><input name="email" type="email" required placeholder="이메일" className="w-full rounded-md border p-3" /><input name="password" type="password" required minLength={12} placeholder="비밀번호 (12자 이상)" className="w-full rounded-md border p-3" /><input name="passwordConfirmation" type="password" required placeholder="비밀번호 확인" className="w-full rounded-md border p-3" />{error && <p className="text-sm text-destructive">{error}</p>}<button className="w-full rounded-md bg-primary p-3 font-medium text-primary-foreground">계정 만들기</button><p className="text-center text-sm">이미 계정이 있나요? <Link to="/login" className="text-primary underline">로그인</Link></p></form></main>;
}
