import { redirect } from "next/navigation";

type LabDetailPageProperties = Readonly<{
  params: Promise<{ readonly id: string }>;
}>;

export default async function LabDetailPage({ params }: LabDetailPageProperties) {
  const { id } = await params;
  redirect("/professors/" + id);
}