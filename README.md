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
