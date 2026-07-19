type ProfessorSaveIconProperties = Readonly<{
  saved: boolean;
}>;

export function ProfessorSaveIcon({ saved }: ProfessorSaveIconProperties) {
  return (
    <svg aria-hidden="true" className="professor-save-icon" focusable="false" viewBox="0 0 24 24">
      <path
        d="M7.25 4.75A1.75 1.75 0 0 1 9 3h6a1.75 1.75 0 0 1 1.75 1.75v15.1L12 16.7l-4.75 3.15V4.75Z"
        fill={saved ? "currentColor" : "none"}
        stroke="currentColor"
        strokeLinejoin="round"
        strokeWidth="1.8"
      />
    </svg>
  );
}
