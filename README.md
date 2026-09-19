# SOS 69069 cSOS v0.4

Android / desktop tool for querying, minting and deploying **SOS 69069 cSOS**.

## Contracts (Ethereum mainnet)

| Contract | Address |
|----------|---------|
| cSOS   | `0xce9B507C242Adf722DD1DE2d7aa5Db1BF2259D8F` |
| LEDGER (immutable) | `0x7373DBC24Dcd785896E8Ac3d5372c6ced9B75a8A` |

The cSOS address is prefilled in the **Query** and **Mint** tabs. Mint
signatures are made on the LEDGER's EIP-712 domain.

## Tabs

Tab order in the app: **Query → Mint → Deploy** (the app opens on Query).

| Tab    | Purpose                                            |
|--------|----------------------------------------------------|
| Query  | Read Push / Trust / Effective / mintable           |
| Mint   | Sign EIP-712 Record + mint cSOS                    |
| Deploy | Deploy a new cSOS contract (MINT_FEE usually 0)    |

## Mint flow

1. Fill RPC + private key + cSOS address
   (or arrive from the Deploy tab via the green "Go to Mint tab" button).
2. Tap **Refresh Status**.
3. Enter an amount, **or leave it blank for Mint Max**.
4. Tap **Sign & Mint**.

The app automatically:

- builds the metadata `cSOS:MINT:<amount>`
- generates a unique `payloadHash` (no need to type one)
- signs the EIP-712 Record on the LEDGER domain
- submits the transaction

## Prefill defaults (editable)

| Field          | Default                                        |
|----------------|------------------------------------------------|
| RPC URL        | https://ethereum-rpc.publicnode.com            |
| Chain ID       | 1 (Ethereum mainnet)                           |
| MINT_FEE       | 0                                              |
| TREASURY       | 0x1C10e6574ee696f54b21A611a21313E4714628ad     |
| cSOS contract  | 0xce9B507C242Adf722DD1DE2d7aa5Db1BF2259D8F     |
| Donation       | 0                                              |

Never prefilled: private key, amount, payloadHash, query address.

## UI (v0.4)

- Text in input fields is vertically centered, sizes use `dp` so it looks the
  same on every phone
- Small caption above every field
- Every tab scrolls; the keyboard pushes the active field into view
- Large touch-friendly buttons
- Plain-text status markers (`[OK]`, `[X]`, `[!]`) instead of emoji, which the
  default Android font cannot render

## Build APK

```bash
buildozer android debug
```

Requires the usual Buildozer / Android SDK / NDK setup. The GitHub workflow in
`.github/workflows/build.yml` builds it automatically and uploads the APK as
the `sos-69069-csos-apk` artifact.

Uninstall any older build before installing a new one (the Android package
name is now `org.sos.sos69069csos`).

## Files that matter

- `main.py` — all logic + UI
- `assets/logo.png` — green star logo
- `icon.png`, `presplash.png` — launcher icon and startup splash
- `buildozer.spec` — packaging
- `README.md` — this file

## Security note

This is a **power-user tool**. It uses a raw private key. Do **not** use it as
a public-facing wallet. For end users, build a wallet-connected web dApp that
never sees the private key. Test on Sepolia before using mainnet.
