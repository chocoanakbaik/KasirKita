# Startup Splash Assets

The splash screen will be designed as a lightweight local desktop screen, not a network-loading page.

Expected elements:

- Approved KasirKita logo once available.
- Product name and tagline: “Usaha Lancar, Kasir Gampang.”
- A clear, restrained progress indicator.
- Short status text only for real startup steps, such as opening the local database or loading settings.
- A fallback path if initialization fails, with a useful error message rather than an endless spinner.

Do not fake progress or display a splash screen for an arbitrary delay. The splash should close when startup work finishes. Keep the artwork lightweight and avoid network dependencies.
