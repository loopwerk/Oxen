<p align="center">
  <img src="logo.png" width="200" alt="Oxen logo" /><br/><br/>
</p>

A simple self-hosted time-tracking and invoicing service, built on Django.

## Why

I've used [Harvest](https://www.getharvest.com/) for over ten years, as a freelance developer. It offered everything that I needed, in a neat little package. No feature bloat, nice UI, affordable price.

But over time it has added bloat, added AI integration, replaced its UI with a worse version, been sold to [Bending Spoons](https://www.reddit.com/r/HarvestApp/comments/1q25xpy/purchase_by_bending_spoons/) and got more expensive. And while Harvest does have a free account (limited to one user and 2 projects), you can't use it to create invoices unless you connect to Stripe to get paid - costing you 2% of your gross revenue!

I went looking for a replacement, but nothing really offered the same minimal features for a low price. If I wanted to self-host something, the list of options got much smaller. So, I decided to build something myself.

## Features

- Fully open source and self-hosted
- Clients and projects, each with their own currency and VAT rates
- Multiple users, with two roles available
- Users can be assigned to specific projects
- Timesheets: keep track of your hours per project, per day
- Invoices: generate beautiful PDF invoices based on hours or free form

What's not included:

- Ads and tracking
- AI features
- Expense tracking
- Per-employee rates
- Costs, budgets, profits
- Tasks
- Teams
- Automated / scheduled invoice generation
- Public invoice links
- Online payments
- Retainers

On the roadmap:

- Reports
- API
- Custom invoice templates
- e-invoices
- Data export & import

## Getting started

### Running on Coolify

1. Create an application with the Docker Compose option, and paste in the contents of [coolify.yml](https://github.com/loopwerk/Oxen/blob/main/coolify.yml).
2. Set the domain.
3. Deploy.
4. Copy the `SERVICE_PASSWORD_SETUPTOKEN` value under Environment Variables.
5. Open your Oxen instance, and on the setup screen paste in the setup token.

### Running elsewhere with Docker Compose

Create an `.env` file with the following values:

```
SECRET_KEY=<secret>
SETUP_TOKEN=<secret>
```

`openssl rand -hex 32` makes a good secret. Behind a reverse proxy, also set `APP_URL` to its public URL, such as `https://hours.example.com`: passkeys only work on that domain.

To build the Docker container and start up with a PostgreSQL database, run:

```
docker compose up -d
```

This will create a PostgreSQL database and start Oxen on http://localhost:8000.

## Settings

The following environment values can be set:

- `TIME_ZONE`, such as `Europe/Amsterdam`. the default is `UTC`. See the [list of timezones](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones).
- `UPDATE_CHECK=false` turns off the daily update check.

## Open source

Oxen is hand-crafted open source code, and available under the MIT license.

## Support

Commercial support is available via [Loopwerk](https://www.loopwerk.io/open-source/support/).
