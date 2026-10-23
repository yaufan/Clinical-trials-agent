"use client";

import { useParams } from "next/navigation";
import { RunWorkspace } from "@/components/run/run-workspace";

export default function RunPage() {
  const params = useParams<{ id: string }>();
  const id = params?.id;
  if (!id) return null;
  return <RunWorkspace runId={id} />;
}
