# siphash.js

A pure Javascript implementation of
[SipHash](https://www.aumasson.jp/siphash/siphash.pdf)

> SipHash is a family of pseudorandom functions optimized for short
> inputs. Target applications include network traffic authentication and
> hash-table lookups protected against hash-flooding denial-of-service
> attacks. SipHash has well-defined security goals and competitive
> performance.

This package also includes an implementation of SipHash128.

## Fork notes
This package is a fork of https://github.com/jedisct1/siphash-js

## Installation

Server-side installation (nodejs):

    $ npm install @posthog/siphash

## Usage

```javascript
import * as siphash from 'siphash';

const key = siphash.string16_to_key("This is the key!");
const message = "Short test message";
const hash_hex = siphash.hash_hex(key, message);
```

A key is an array of 4 integers, and each of them will be clamped to
32 bits in order to build a 128-bit key.
For a random key, just generate 4 random integers instead of calling
`string16_to_key()`.

```javascript
import * as siphash from 'siphash'

const key = [0xdeadbeef, 0xcafebabe, 0x8badf00d, 0x1badb002];
const message = "Short test message";
const hash_hex = siphash.hash_hex(key, message);
```

The 64-bit hash can also be obtained as two 32-bit values with
`hash(key, message)`:

```javascript
import * as siphash from 'siphash'

const key = [0xdeadbeef, 0xcafebabe, 0x8badf00d, 0x1badb002];
const message = "Short test message";
const hash = siphash.hash(key, message);
const hash_msb = hash.h;
const hash_lsb = hash.l;
```

A 53-bit unsigned integer can be obtained with `hash_uint(key, message)`:

```javascript
import * as siphash from 'siphash'

const key = siphash.string16_to_key("0123456789ABCDEF");
const message = "Short test message";
const index = siphash.hash_uint(key, message);
```


## SipHash-double

```javascript
import * as siphash from 'siphash/lib/siphash-double';

const key = siphash.string16_to_key("This is the key!");
const message = "Short test message";
const hash_hex = siphash.hash_hex(key, message);
```