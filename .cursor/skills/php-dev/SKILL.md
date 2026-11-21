---
name: php-dev
description: >-
  PHP development workflow in Docker: Composer dependency management, PHPUnit tests,
  PHPStan static analysis, PHP-CS-Fixer (PER Coding Style), Rector upgrades, composer
  audit, and the `make check` deterministic gate. Use when running PHP scripts or tests,
  checking code quality, managing Composer packages, or setting up the quality gate for
  a PHP, Symfony, or Laravel project.
---

# PHP Development Workflow


Coding standards: `rules/240-php.mdc`.

## Prerequisites


- Docker Compose environment is running: `docker compose up -d`.
- Check `docker-compose.yml` for the PHP service name (commonly `php`, `app`, `backend`).
  The image must contain Composer (`COPY --from=composer:2 /usr/bin/composer /usr/bin/composer`).
- `composer.json` declares `require.php` and PSR-4 autoload; `composer.lock` is committed.

## Running Scripts


```bash
docker compose exec <service> php bin/console <command>   # Symfony
docker compose exec <service> php artisan <command>       # Laravel
docker compose exec <service> php scripts/import.php --dry-run

# Interactive shell (PsySH, if installed as dev dependency)
docker compose exec -it <service> vendor/bin/psysh
```

## Dependency Management (Composer)


```bash
# Reproducible install from the lockfile
docker compose exec <service> composer install

# Add a runtime / dev dependency
docker compose exec <service> composer require vendor/package
docker compose exec <service> composer require --dev vendor/package

# Update one package deliberately (never a blind `composer update` of everything)
docker compose exec <service> composer update vendor/package --with-dependencies

# Validate composer.json / lock consistency
docker compose exec <service> composer validate --strict

# Known vulnerabilities and outdated packages
docker compose exec <service> composer audit
docker compose exec <service> composer outdated --direct
```

> If `vendor/` is baked into the image (not bind-mounted), rebuild after any
> `composer.json` change: `docker compose build <service> && docker compose up -d <service>`.
>
Production image install (Dockerfile, multi-stage — see `040-docker-standards.mdc`):

```dockerfile
RUN composer install --no-dev --no-interaction --prefer-dist --classmap-authoritative
```

## Tests (PHPUnit)


```bash
# All tests
docker compose exec <service> vendor/bin/phpunit

# Single file / single test method
docker compose exec <service> vendor/bin/phpunit tests/Billing/InvoiceCalculatorTest.php
docker compose exec <service> vendor/bin/phpunit --filter chunkWithEmptyInputReturnsEmptyList

# By group (#[Group('integration')])
docker compose exec <service> vendor/bin/phpunit --group integration
docker compose exec <service> vendor/bin/phpunit --exclude-group slow

# Coverage (requires pcov or Xdebug in the dev image)
docker compose exec <service> vendor/bin/phpunit --coverage-text
```

`phpunit.xml.dist` essentials:

```xml
<phpunit bootstrap="vendor/autoload.php" colors="true"
         failOnRisky="true" failOnWarning="true" failOnDeprecation="true"
         cacheDirectory=".phpunit.cache">
  <testsuites>
    <testsuite name="default"><directory>tests</directory></testsuite>
  </testsuites>
  <source><include><directory>src</directory></include></source>
</phpunit>
```

## Static Analysis (PHPStan)


```bash
docker compose exec <service> vendor/bin/phpstan analyse --no-progress

# Legacy code only: (re)generate a baseline — it may only shrink afterwards
docker compose exec <service> vendor/bin/phpstan analyse --generate-baseline
```

`phpstan.neon.dist`:

```neon
includes:
    - vendor/phpstan/phpstan-strict-rules/rules.neon
parameters:
    level: max
    paths:
        - src
        - tests
```

## Code Style (PHP-CS-Fixer)


```bash
# Check only (CI / gate)
docker compose exec <service> vendor/bin/php-cs-fixer check --diff

# Fix
docker compose exec <service> vendor/bin/php-cs-fixer fix
```

`.php-cs-fixer.dist.php`:

```php
<?php

declare(strict_types=1);

return (new PhpCsFixer\Config())
    ->setRiskyAllowed(true)
    ->setRules([
        '@PER-CS' => true,
        'declare_strict_types' => true,
        'strict_comparison' => true,
        'no_unused_imports' => true,
    ])
    ->setFinder(PhpCsFixer\Finder::create()->in([__DIR__ . '/src', __DIR__ . '/tests']));
```

## Upgrades and Refactoring (Rector)


```bash
# Always dry-run first and review the diff; apply only as a separate, reviewable change
docker compose exec <service> vendor/bin/rector process --dry-run
docker compose exec <service> vendor/bin/rector process
```

## Deterministic Gate — `make check`


The Coder, the Reviewer, and CI run the exact **same** command (see
`rules/090-apm-orchestration.mdc`). Copy the shipped template once per project:

```bash
# One-time setup per project
cp .cursor/skills/php-dev/templates/Makefile ./Makefile
mkdir -p .github/workflows
cp .cursor/skills/python-dev/templates/ci.yml .github/workflows/ci.yml   # stack-agnostic: runs `make check`
# Edit SERVICE in the Makefile if your compose service isn't named "app"
```

```bash
make check            # composer validate, php-cs-fixer check, phpstan, phpunit
make check RUNNER=    # native run (Docker-exempt project)
make audit            # separate: composer audit (not deterministic)
```

## Container Shell


```bash
# Alpine-based images (php:*-fpm-alpine)
docker compose exec -it <service> sh

# Debian-based images; as root for permission debugging
docker compose exec -it <service> bash
docker compose exec -it -u root <service> bash
```
