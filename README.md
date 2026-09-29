### Iraqi Passport Management

Iraqi Passport Issuance Lifecycle Management

### Supported Runtime

- Frappe Framework 16.33.x
- Python 3.14.x
- Node.js 24.x
- MariaDB 11.8.x
- Redis 8.x

Production deployments should use the versions supplied and supported by the
target Frappe Press environment. `bench start` is for development only.

### Frappe Press Deployment

This repository is a Frappe app and is intended to be deployed by Frappe Press
as part of a bench. Press owns the bench, site, database, Redis, workers, and
reverse proxy; no Dockerfile, Procfile, or application server is required here.

Before deploying:

1. Push this repository to a Git provider that Press can access.
2. Add the repository as a custom app in Press and select the release branch.
3. Add the app to the target bench and deploy the bench.
4. Install `iraqi_passport` on the target site from the bench's site app list.
5. Run the deployment and verify migrations, fixtures, permissions, workflows,
   and print formats in a staging site before promoting to production.

The app declares its OS-level build dependencies in `pyproject.toml` under
`[deploy.dependencies.apt]`, which is the app-level dependency configuration
consumed by Frappe Cloud/Press. Keep infrastructure settings such as database
credentials, Redis endpoints, workers, backups, domains, and TLS in Press,
never in this repository.

For an update, deploy a new immutable commit or tag, let Press run migrations,
and verify the site before switching traffic. Keep the previous commit
available for rollback and take a site backup before schema-affecting releases.

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch N
bench install-app iraqi_passport
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/iraqi_passport
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade
### CI

This app can use GitHub Actions for CI. The following workflows are configured:

- CI: Installs this app and runs unit tests on every push to `develop` branch.
- Linters: Runs [Frappe Semgrep Rules](https://github.com/frappe/semgrep-rules) and [pip-audit](https://pypi.org/project/pip-audit/) on every pull request.


### License

mit
