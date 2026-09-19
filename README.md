# SOS 69069 cSOS

**Android / desktop tool for querying, minting and deploying SOS 69069 cSOS.**

SOS 69069 originates from verified Activity and Signatures.  
Whatever you do. SOS records. Whatever you do. Continue ...

---

## What is cSOS?

**cSOS** (“Capped SOS”) is a **transferable ERC-20 token** that sits on top of the immutable SOS 69069 ledger.

### The SOS 69069 Ledger

SOS 69069 (`0x7373DBC24Dcd785896E8Ac3d5372c6ced9B75a8A`) is a pure on-chain **event ledger of presence**. It:

- Holds **no assets**
- Executes **nothing** on behalf of users
- Has **no admin, owner, or upgrade path**
- Only records signed data as permanent events

Every successful record contains:

- the **signer**
- the **intended address**
- a **payload hash**
- the **raw signature**
- free-form **metadata**

Writing a record increments two independent counters:

- `pushOf[signer]`
- `trustOf[intendedTo]`

The **effective** value for any address is defined as:

```text
effective = trustOf − pushOf
```

This signed integer is exposed through `effectiveOf()`. For wallet-style display it is cast to a non-negative value via `balanceOf()` → `max(0, effective)`.

From the outside the ledger presents a familiar ERC-20 surface (`name`, `symbol`, `decimals`, `balanceOf`, Transfer events), but **nothing is ever transferred**. It is purely a permanent, identityless record of presence.

### How cSOS relates to the Ledger

cSOS is a **read-only wrapper** over the SOS 69069 ledger. It mints a real, transferable ERC-20 against a user’s current **effective** metric under a hard, immutable rule:

```text
maximum cumulative cSOS a user can ever mint
= max(0, effectiveOf(user) − 10)
```

- Permanent **RESERVE = 10**
- Examples:
  - effective = 39 → maximum mintable = 29
  - effective = 100 → maximum mintable = 90
  - effective ≤ 10 → maximum mintable = 0

cSOS itself is a normal ERC-20 (`name = "Capped SOS"`, `symbol = "cSOS"`, `decimals = 0`) and is fully compatible with DEXes / LPs.

---

## How Minting Works (Exact Flow)

Every mint is **user-signed** and permanently recorded on the SOS 69069 ledger. There is no trusted key, no privileged submitter, and no auditor role.

### 1. Eligibility check
```text
mintable(user) = max(0, effectiveOf(user) − 10 − alreadyMinted[user])
```

### 2. User prepares an EIP-712 Record on the LEDGER domain
```text
Record(
    signer      = user,
    intendedTo  = user,          // always self
    payloadHash = unique-per-mint bytes32,   // app generates this
    metadata    = "cSOS:MINT:<amount>"       // e.g. "cSOS:MINT:5"
)
```

The signature is produced over the **LEDGER’s** EIP-712 domain (not the cSOS contract).

### 3. Submission
The app (or any caller) calls one of:

- `mint(amount, payloadHash, signature)`
- `mintMax(payloadHash, signature)`

### 4. On-chain execution (cSOS contract)
1. Re-computes the expected struct hash via the ledger.
2. Checks the amount does not exceed the remaining mintable quota.
3. Marks the hash as used (local + ledger-level replay protection).
4. Calls `LEDGER.recordSignature(...)` — this permanently stores the signed Record on the SOS 69069 ledger and increments the user’s `pushOf` (and therefore changes their future effective).
5. Verifies the ledger consumed the hash.
6. Mints the corresponding amount of cSOS to the user.

### Key properties
- Every mint leaves an immutable, ECDSA-verified footprint on the SOS 69069 ledger.
- The ledger record is the source of truth; the cSOS contract only mirrors it.
- No admin can pause, blacklist, or reverse a mint.
- Optional `MINT_FEE` (usually set to 0) and voluntary ETH donations are handled via permissionless pull functions.

---

## Contracts (Ethereum mainnet)

| Contract              | Address                                      |
|-----------------------|----------------------------------------------|
| **cSOS**              | `0xce9B507C242Adf722DD1DE2d7aa5Db1BF2259D8F` |
| **LEDGER** (immutable)| `0x7373DBC24Dcd785896E8Ac3d5372c6ced9B75a8A` |

The cSOS address is prefilled in the Query and Mint tabs.  
Mint signatures are always made on the **LEDGER’s** EIP-712 domain.

---

## App Tabs

Tab order: **Query → Mint → Deploy** (app opens on Query).

| Tab     | Purpose                                              |
|---------|------------------------------------------------------|
| **Query**  | Read Push / Trust / Effective / mintable            |
| **Mint**   | Sign EIP-712 Record + mint cSOS                     |
| **Deploy** | Deploy a new cSOS contract (MINT_FEE usually 0)     |

### Mint flow (user steps)

1. Fill RPC + private key + cSOS address  
   (or arrive from the Deploy tab via the green “Go to Mint tab” button).
2. Tap **Refresh Status**.
3. Enter an amount, or leave blank for **Mint Max**.
4. Tap **Sign & Mint**.

The app automatically:

- builds the metadata `cSOS:MINT:<amount>`
- generates a unique `payloadHash` (you never type one)
- signs the EIP-712 Record on the LEDGER domain
- submits the transaction

### Prefill defaults (editable)

| Field            | Default                                              |
|------------------|------------------------------------------------------|
| RPC URL          | `https://ethereum-rpc.publicnode.com`                |
| Chain ID         | `1` (Ethereum mainnet)                               |
| MINT_FEE         | `0`                                                  |
| TREASURY         | `0x1C10e6574ee696f54b21A611a21313E4714628ad`         |
| cSOS contract    | `0xce9B507C242Adf722DD1DE2d7aa5Db1BF2259D8F`         |
| Donation         | `0`                                                  |

**Never prefilled:** private key, amount, payloadHash, query address.

---

## UI (v0.4)

- Text in input fields is vertically centered; sizes use `dp` so it looks the same on every phone
- Small caption above every field
- Every tab scrolls; the keyboard pushes the active field into view
- Large touch-friendly buttons
- Plain-text status markers (`[OK]`, `[X]`, `[!]`) instead of emoji (default Android font cannot render them)

---

## Build APK

```bash
buildozer android debug
```

Requires the usual Buildozer / Android SDK / NDK setup.  
The GitHub workflow in `.github/workflows/build.yml` builds it automatically and uploads the APK as the `sos-69069-csos-apk` artifact.

**Uninstall any older build** before installing a new one  
(the Android package name is now `org.sos.sos69069csos`).

---

## Files that matter

| File                | Purpose                          |
|---------------------|----------------------------------|
| `main.py`           | All logic + UI                   |
| `assets/logo.png`   | Green star logo                  |
| `icon.png`          | Launcher icon                    |
| `presplash.png`     | Startup splash                   |
| `buildozer.spec`    | Packaging configuration          |
| `README.md`         | This file                        |

---

## Security note

This is a **power-user tool**. It uses a raw private key.  
Do **not** use it as a public-facing wallet.

For end users, build a wallet-connected web dApp that never sees the private key.  
**Test on Sepolia before using mainnet.**
