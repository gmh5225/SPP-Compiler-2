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
    TkTripleDot = "..."
    TkColon = ":"

    TkDot = "."
    TkComma = ","
    TkAssign = "="
    TkArrowReturn = "->"
    TkArrowRFat = "=>"
    TkAt = "@"
    TkUnderscore = "_"

    TkEOF = "\0"
    TkWhitespace = " "
    TkNewLine = "\n"

    KwMod = "mod"
    KwUse = "use"
    KwEnum = "enum"
    KwFn = "fn"
    KwGn = "gn"
    KwMut = "mut"
    KwLet = "let"
    KwIf = "if"
    KwElse = "else"
    KwWhile = "while"
    KwRet = "ret"
    KwYield = "yield"
    KwCls = "cls"
    KwWhere = "where"
    KwTrue = "true"
    KwFalse = "false"
    KwAs = "as"
    KwSup = "sup"
    KwWith = "with"
    KwSelf = "Self"
    KwFor = "for"

    # Don't change order of these (regex are matched in this order)
    # 0x12 must be HexDigits not DecDigits(0) then Identifier(x12)
    LxIdentifier = r"[a-z][_a-zA-Z0-9]*"
    LxUpperIdentifier = r"[A-Z][_a-zA-Z0-9]*"
    LxBinDigits = r"0b[01]+"
    LxHexDigits = r"0x[0-9a-fA-F]+"
    LxDecDigits = r"[0-9]([0-9_]*[0-9])?"
    LxDoubleQuoteStr = r"\".*\""
    LxSingleQuoteChr = r"'.?'"
    LxRegex = r"r\".*\""
    LxSingleLineComment = r"#.*"
    LxMultiLineComment = r"/\*.*\*/"


@dataclass
class Token:
    token_metadata: str
    token_type: TokenType
