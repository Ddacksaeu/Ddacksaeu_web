import { notFound } from "next/navigation";

import { AppHeader } from "../../../src/components/app-header";
import { RealLabDetail } from "../../../src/features/labs/real-lab-detail";
import { isShowcaseMode, SHOWCASE_UNAVAILABLE_MESSAGE } from "../../../src/features/showcase/mode";
import { fetchBackendLab, fetchBackendSimilarLabs } from "../../../src/server/backend/labs";

type Props = Readonly<{ params: Promise<{ readonly id: string }> }>;

export default async function ProfessorDetailPage({ params }: Props) {
  const { id } = await params;
  if (isShowcaseMode()) {
    return <div className="site-shell"><AppHeader current="professors" /><main className="profile-layout"><section className="profile-intro"><p className="kicker">PROFESSOR DISCOVERY</p><h1>Professor details are available locally</h1><p>{SHOWCASE_UNAVAILABLE_MESSAGE}</p></section></main></div>;
  }
  const [lab, similar] = await Promise.all([fetchBackendLab(id), fetchBackendSimilarLabs(id)]);
  if (lab === null) notFound();
  return <div className="site-shell"><AppHeader current="professors" /><RealLabDetail lab={lab} similar={similar} /></div>;
}
