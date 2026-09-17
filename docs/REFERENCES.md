# Implementation references

Official/primary sources consulted on 16 September 2026. URLs are reference documentation, not application data sources. No learner data is sent to them by the core application.

- Next.js installation and runtime requirements: https://nextjs.org/docs/app/getting-started/installation
- Pydantic strict validation: https://docs.pydantic.dev/latest/concepts/strict_mode/
- Pydantic validators: https://docs.pydantic.dev/latest/concepts/validators/
- Zod schemas and strict objects: https://zod.dev/api
- FastAPI file upload interface: https://fastapi.tiangolo.com/tutorial/request-files/
- Typst Python binding and `sys_inputs`: https://pypi.org/project/typst/
- Typst reference: https://typst.app/docs/reference/
- pdfplumber extraction API: https://github.com/jsvine/pdfplumber
- Auth.js Next.js installation: https://authjs.dev/getting-started/installation
- Auth.js beta.32 release (pinned optional authentication package): https://github.com/nextauthjs/next-auth/releases/tag/next-auth%405.0.0-beta.32
- Auth.js GitHub provider setup: https://authjs.dev/guides/configuring-github

## Dependency and licence notes

No PyMuPDF dependency is used. No font files or downloaded third-party source archives are bundled. Font installation is an operator/build-time step. Fonts embedded in the fictional example PDF are part of the rendered document, not separately distributed font files.

The skill dictionary was authored for this starter and uses internal skill IDs. It is not presented as a licensed/imported O*NET or ESCO corpus. Keep attribution/licence metadata when replacing it with external taxonomy content.

Review actual resolved dependency licences and security advisories before publishing or commercial deployment. Generated application code does not remove obligations associated with its dependencies. The repository does not choose a publication licence for your company.
