from dataclasses import dataclass
from enum import Enum


class TokenType(Enum):
    # Logical operations (AND, OR, NOT)
    TkDoubleAmpersand = "&&"
    TkDoubleAmpersandEquals = "&&="
    TkDoublePipe = "||"
    TkDoublePipeEquals = "||="

    # Bitwise operations (AND, OR, XOR, NOT, SHL, SHR, ROL, ROR)
    TkAmpersand = "&"# Also used for references
    TkAmpersandEquals = "&="
    TkPipe = "|"
    TkPipeEquals = "|="
    TkCaret = "^"
    TkCaretEquals = "^="
    TkDoubleAngleL = "<<"
    TkDoubleAngleLEquals = "<<="
    TkDoubleAngleR = ">>"
    TkDoubleAngleREquals = ">>="
    TkTripleAngleL = "<<<"
    TkTripleAngleLEquals = "<<<="
    TkTripleAngleR = ">>>"
    TkTripleAngleREquals = ">>>="

    # Comparison operations (EQ, NE, LE, GE, LT, GT, CMP)
    TkEq = "=="
    TkNe = "!="
    TkLe = "<="
    TkGe = ">="
    TkLt = "<"
    TkGt = ">"
    TkSs = "<=>"

    # Arithmetic operations (ADD, SUB, MUL, DIV, REM)
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

    # Brackets (PAREN, BRACK, BRACE)
    TkParenL = "("
    TkParenR = ")"
    TkBrackL = "["
    TkBrackR = "]"
    TkBraceL = "{"
    TkBraceR = "}"

    # Other symbols
    TkQst = "?"
    TkTripleDot = "..."
    TkColon = ":"

    TkDot = "."
    TkComma = ","
    TkAssign = "="
    TkArrowR = "->"
    TkAt = "@"
    TkUnderscore = "_"

    TkEOF = "\0"
    TkWhitespace = " "
    TkNewLine = "\n"

    # Keywords
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
    KwFor = "for"
    KwSelf = "self"
    KwSelfType = "Self"

    # Don't change order of these (regex are matched in this order)
    # 0x12 must be HexDigits not DecDigits(0) then Identifier(x12)
    LxIdentifier = r"[a-z][_a-zA-Z0-9]*"
    LxUpperIdentifier = r"[A-Z][_a-zA-Z0-9]*"
    LxBinDigits = r"0b[01]+"
    LxHexDigits = r"0x[0-9a-fA-F]+"
    LxDecDigits = r"[0-9]([0-9_]*[0-9])?"
    LxDoubleQuoteStr = r"\"[^\"]*\""
    LxRegex = r"r\".*\""
    LxSingleLineComment = r"#.*"
    LxMultiLineComment = r"/\*.*\*/"


@dataclass
class Token:
    token_metadata: str
    token_type: TokenType
