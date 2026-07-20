import { notFound } from "next/navigation";

import { AppHeader } from "../../../src/components/app-header";
import { RealLabDetail } from "../../../src/features/labs/real-lab-detail";
import { fetchBackendLab, fetchBackendSimilarLabs } from "../../../src/server/backend/labs";

type Props = Readonly<{ params: Promise<{ readonly id: string }> }>;

export default async function ProfessorDetailPage({ params }: Props) {
  const { id } = await params;
  const [lab, similar] = await Promise.all([fetchBackendLab(id), fetchBackendSimilarLabs(id)]);
  if (lab === null) notFound();
  return <div className="site-shell"><AppHeader current="professors" /><RealLabDetail lab={lab} similar={similar} /></div>;
}
