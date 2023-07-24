from dataclasses import dataclass
from enum import Enum

class TokenType(Enum):
    # Used for logical operations (AND, OR, NOT)
    TkDoubleAmpersand = "&&"
    TkDoubleAmpersandEquals = "&&="
    TkDoublePipe = "||"
    TkDoublePipeEquals = "||="

    # Used for bitwise operations (AND, OR, XOR, NOT, SHL, SHR, ROL, ROR)
    TkAmpersand = "&"# Also used for references
    TkAmpersandEquals = "&="
    TkPipe = "|"
    TkPipeEquals = "|="
    TkCaret = "^"
    TkCaretEquals = "^="

    TkEq = "=="
    TkNe = "!="
    TkLe = "<="
    TkGe = ">="
    TkLt = "<"
    TkGt = ">"
    TkSs = "<=>"

    TkAdd = "+"
    TkSub = "-"
    TkMul = "*"
    TkDiv = "/"
    TkRem = "%"
    TkAddEq = "+="
    TkSubEq = "-="
    TkMulEq = "*="
    TkDivEq = "/="
    TkRemEq = "%="

    TkParenL = "("
    TkParenR = ")"
    TkBrackL = "["
    TkBrackR = "]"
    TkBraceL = "{"
    TkBraceR = "}"

    TkQst = "?"

    TkPipeArrowR = "|>"
    TkPipeArrowL = "<|"
    TkDoubleDot = ".."
    TkTripleDot = "..."
    TkColon = ":"

    TkDynaRes = "."
    TkStatRes = "::"
    TkComma = ","
    TkAssign = "="
    TkArrowReturn = "->"
    TkArrowRFat = "=>"
    TkAt = "@"
    TkUnderscore = "_"

    TkSemicolon = ";"
    TkEOF = "\0"
    TkWhitespace = " "
    TkNewLine = "\n"

    KwMod = "mod"
    KwUse = "use"
    KwEnum = "enum"
    KwIn = "in"
    KwFn = "fn"
    KwGn = "gn"
    KwMut = "mut"
    KwLet = "let"
    KwIf = "if"
    KwElse = "else" # -- change how `if` works
    KwWhile = "while" # -- unify with `for`
    KwFor = "for"
    KwDo = "do" # -- unify with `for`
    KwReturn = "ret"
    KwYield = "yield"
    KwCls = "cls"
    KwWhere = "where" # -- replace with `if`?
    KwTrue = "true" # -- use std::Bool::True()
    KwFalse = "false" # -- use std::Bool::False()
    KwAs = "as"
    KwSup = "sup"
    KwWith = "with"
    KwBreak = "break" # -- might be removing breaks => remove labels
    KwContinue = "cont" # -- might be removing continues => remove labels
    KwSelf = "Self"

    # Don't change order of these (regex are matched in this order)
    # 0x12 must be HexDigits not DecDigits(0) then Identifier(x12)
    LxIdentifier = r"[_a-zA-Z][_a-zA-Z0-9]*"
    # LxTypeIdentifier = r"[A-Z][_a-zA-Z0-9]*"
    LxBinDigits = r"0b[01]+"
    LxHexDigits = r"0x[0-9a-fA-F]+"
    LxDecDigits = r"[0-9]+"
    LxDoubleQuoteStr = r"\".*\""
    LxSingleQuoteChr = r"'.?'"
    LxRegex = r"r\".*\""
    LxTag = r"\'[a-zA-Z0-9_]+"
    LxSingleLineComment = r"#.*"
    LxMultiLineComment = r"/\*.*\*/"


@dataclass
class Token:
    token_metadata: str
    token_type: TokenType
