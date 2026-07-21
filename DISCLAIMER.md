# Disclaimer & Responsible Use

This project automates seat/room reservations on [anny.eu](https://anny.eu) for
university libraries via your own SSO login. It is an independent, unofficial
tool and is **not affiliated with anny GmbH or any university**.

Please use it responsibly:

- **Respect the terms of service** of anny and your institution. You are solely
  responsible for how you use this tool and for any consequences to your account.
- **It books only what you could book by hand.** It logs in as you, reserves one
  spot per time window, and stops. It does not exploit any vulnerability.
- **No spamming.** The tool deliberately makes a small number of calm requests at
  the real opening time — it does not flood the server, and doing so would only
  get your account rate-limited. Please keep it that way; do not crank the
  concurrency settings up to hammer the service. That is unfair to other students
  and can degrade the service for everyone.
- **Don't hoard.** Booking many seats you won't use denies them to others. The
  defaults intentionally book a single spot per window.
- **Credentials stay yours.** Your username/password live only in your local
  `.env` (git-ignored) or your CI secrets. Never commit them.

If you rely on this for something important, double-check your reservation in the
anny UI — software can fail, SSO flows change, and libraries adjust their rules.

The software is provided "as is", without warranty of any kind. See
[LICENSE](LICENSE).
