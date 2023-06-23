from dataclasses import dataclass
from enum import Enum

class TokenType(Enum):
    # Used for logical operations (AND, OR, NOT)
    TkDoubleAmpersand = "&&"
    TkDoubleAmpersandEquals = "&&="
    TkDoubleVerticalBar = "||"
    TkDoubleVerticalBarEquals = "||="
    TkExclamation = "!"

    # Used for bitwise operations (AND, OR, XOR, NOT, SHL, SHR, ROL, ROR)
    TkAmpersand = "&"# Also used for references
    TkAmpersandEquals = "&="
    TkVerticalBar = "|"
    TkVerticalBarEquals = "|="
    TkCaret = "^"
    TkCaretEquals = "^="
    TkTilde = "~"
    TkDoubleLeftAngleBracket = "<<"
    TkDoubleLeftAngleBracketEquals = "<<="
    TkDoubleRightAngleBracket = ">>"
    TkDoubleRightAngleBracketEquals = ">>="
    TkTripleLeftAngleBracket = "<<<"
    TkTripleLeftAngleBracketEquals = "<<<="
    TkTripleRightAngleBracket = ">>>"
    TkTripleRightAngleBracketEquals = ">>>="

    TkDoubleEqual = "=="
    TkExclamationEqual = "!="
    TkLeftAngleBracketEquals = "<="
    TkRightAngleBracketEquals = ">="
    TkLeftAngleBracket = "<" # Also used for generics
    TkRightAngleBracket = ">" # Also used for generics
    TkDoubleFatArrow = "<=>"

    TkPlus = "+"
    TkPlusEquals = "+="
    TkHyphen = "-"
    TkHyphenEquals = "-="
    TkAsterisk = "*"
    TkAsteriskEquals = "*="
    TkForwardSlash = "/"
    TkForwardSlashEquals = "/="
    TkDoubleForwardSlash = "//"
    TkDoubleForwardSlashEquals = "//="
    TkPercent = "%"
    TkPercentEquals = "%="
    TkDoubleAstrix = "**"
    TkDoubleAstrixEquals = "**="

    TkLeftParenthesis = "("
    TkRightParenthesis = ")"
    TkLeftBracket = "["
    TkRightBracket = "]"
    TkLeftBrace = "{"
    TkRightBrace = "}"

    TkQuestionMark = "?"
    TkDoubleQuestionMark = "??"
    TkQuestionMarkColon = "?:"

    TkPipe = "|>"
    TkDoubleDot = ".."
    TkTripleDot = "..."
    TkColon = ":"

    TkDot = "."
    TkDoubleColon = "::"
    TkComma = ","
    TkEqual = "="
    TkRightArrow = "->"
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
    KwPub = "pub"
    KwProt = "prot"
    KwPriv = "priv"
    KwPart = "part"
    KwAsync = "async"
    KwFun = "fun"
    KwMut = "mut"
    KwLet = "let"
    KwIf = "if"
    KwElif = "elif"
    KwElse = "else"
    KwWhile = "while"
    KwFor = "for"
    KwDo = "do"
    KwMatch = "match"
    KwCase = "case"
    KwReturn = "return"
    KwYield = "yield"
    KwCls = "cls"
    KwAwait = "await"
    KwWhere = "where"
    KwTrue = "true"
    KwFalse = "false"
    KwAs = "as"
    KwSup = "sup"
    KwWith = "with"
    KwBreak = "break"
    KwContinue = "continue"

    LxIdentifier = r"[_a-zA-Z][_a-zA-Z0-9]*"
    LxBinDigits = r"0b[01]+"
    LxDecDigits = r"[0-9]+"
    LxHexDigits = r"0x[0-9a-fA-F]+"
    LxDoubleQuoteStr = r"\".*\""
    LxSingleQuoteChr = r"'.?'"
    LxRegex = r"r\".*\""


@dataclass
class Token:
    token_metadata: str
    token_type: TokenType
