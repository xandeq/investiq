import { redirect } from "next/navigation";

// Landing page — redirects to login until dashboard is built in Plan 01-02
export default function Home() {
  redirect("/login");
}
