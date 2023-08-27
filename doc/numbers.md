# Numbers
- 1 `Num` class, encompassing integer, fractional and imaginary numbers.
- The "small number optimization" allows for no performance drop when using small numbers.

## Literals
### Hex
- Starts with `0x`.
- Only valid characters are `0-9` and `a-f`.
- Case insensitive.

### Binary
- Starts with `0b`.
- Only valid characters are `0` and `1`.

### Decimal
- Sign is optional.
- Integer is required.
- Fractional is optional.
- Exponent is optional.
  - `e` or `E` is required.
  - Sign is optional.
  - Integer is required.
- Can be imaginary
  - `i` or `I` is required.

#### Separators
- `_` can be used to separate digits.