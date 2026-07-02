import Link from "next/link";
import { Button, Card, Disclaimer } from "@/components/ui";

export default function Home() {
  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-6 px-6 py-16">
      <h1 className="text-4xl font-bold text-brand">Francessca</h1>
      <p className="text-lg text-slate-700">
        Get organized before you speak with a lawyer. Francessca asks the right
        questions, collects your facts, helps fill standard forms, and produces a
        structured summary you can hand to a qualified lawyer in Germany.
      </p>
      <Card>
        <div className="flex gap-3">
          <Link href="/login">
            <Button>Get started</Button>
          </Link>
          <Link href="/lawyers">
            <Button className="bg-slate-700 hover:bg-slate-800">
              Find a lawyer
            </Button>
          </Link>
        </div>
        <Disclaimer />
      </Card>
    </main>
  );
}
