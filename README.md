<div align="center">

# RatterAU's Apps

**One link to install and update all my iPhone apps**, with LiveContainer, SideStore or AltStore.

### [ratterau.github.io/apps](https://ratterau.github.io/apps/)

<sub>Open that page on your iPhone and tap the button for the app you use.</sub>

</div>

---

## Add the source

| You use | Do this | App limit |
|:--|:--|:--|
| **LiveContainer** (recommended) | [Open the page](https://ratterau.github.io/apps/) on your iPhone and tap **LiveContainer**. Or in LiveContainer: **Sources → +**, paste the URL below | **Doesn't count.** Apps run inside LiveContainer |
| **SideStore** | Tap **SideStore** on [the page](https://ratterau.github.io/apps/). Or **Sources → +**, paste the URL | Each app uses one of your 3 slots |
| **AltStore** | Tap **AltStore** on [the page](https://ratterau.github.io/apps/). Or **Browse → Sources → +**, paste the URL | Each app uses one of your 3 slots |

```
https://ratterau.github.io/apps/source.json
```

> [!IMPORTANT]
> **Using LiveContainer + SideStore?** Add the source in **LiveContainer's own Sources tab**, not in the SideStore inside it. SideStore installs apps as normal apps, so each one would use up an app slot. LiveContainer keeps them inside itself, where they don't count.

New to all of this? Each app's README has a full step-by-step guide to setting up LiveContainer + SideStore from scratch.

## What's in it

| | App | |
|:--:|:--|:--|

## How it stays current

The source isn't edited by hand. [A workflow](.github/workflows/update-source.yml) runs every 6 hours and rebuilds [`source.json`](source.json) from each app's GitHub releases. It downloads every IPA and reads the bundle ID, version, minimum iOS and permission descriptions from the app itself, so what the store shows always matches what you install. Each version also lists its SHA-256.

To add an app or change a description, edit [`config/apps.json`](config/apps.json). To rebuild locally: `python3 scripts/build_source.py` (standard library only).

## Licence

MIT. Each app has its own licence in its repository.
