import Link from 'next/link';
export default function Privacy() {
  return <main className="policy"><Link href="/" className="back-link">Back to studio</Link>
    <div className="eyebrow">PRODUCT PRIVACY NOTES</div><h1>Your resume is personal.</h1>
    <p className="lead">This application sends your resume and job description to the company-operated FastAPI service when you request analysis, rewriting, import or export. It is not a browser-only application.</p>
    <h2>Anonymous processing</h2><p>The application does not intentionally save anonymous resumes to a database. Processing uses memory and short-lived workers. The editor does not use analytics, advertising pixels, session replay, or automatic local storage. Download a workspace before refreshing to keep your work.</p>
    <h2>Optional history</h2><p>When enabled, signed-in users may explicitly save encrypted snapshots. Snapshots expire after 30 days. A cleanup task runs every five minutes while the API is operating; history requests also remove expired entries. Operators must monitor cleanup and manage database backups and their separate retention. You can delete your snapshots from the studio. OAuth providers and hosting infrastructure have their own data practices.</p>
    <h2>Optional external services</h2><p>No model is configured by default. An enabled model receives bullet text only after a separate opt-in; bullets may still contain personal information. GitHub inspection sends a public repository identifier to GitHub after confirmation. Inspected files are not executed.</p>
    <h2>What the checks mean</h2><p>Source checks preserve user-provided statements; they cannot establish their truth. Skill coverage is not proficiency, hiring probability or an employer's internal ranking. PDF extraction checks do not guarantee compatibility with every recruitment system.</p>
    <h2>Age eligibility</h2><p>This starter release is for people aged 18 and above. Age declaration is not identity verification. Support for minors requires a separately reviewed consent flow.</p>
    <h2>Operator configuration required</h2><p>Before a public launch, the company must publish its identity, privacy contact, purposes, legal basis where required, processor information, actual retention and deletion rules, and grievance process. This page is a technical disclosure, not a completed legal notice.</p>
  </main>;
}
