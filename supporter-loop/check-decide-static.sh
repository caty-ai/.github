#!/usr/bin/env bash
# Contract §4.4. Conservative source scanner, not a general YAML/shell evaluator.
# Unsupported dynamic Contents targets fail closed; keep ledger/ visible in code.
set -euo pipefail
if [ "$#" -ne 1 ] || [ ! -f "$1" ]; then
  echo 'usage: check-decide-static.sh <workflow.yml>' >&2
  exit 2
fi
awk '
function hit(rule, n, why) {
  if (data_only && rule!="a-prime") return
  print FILENAME ":" n ": " rule ": " why
  if (rule=="d") unsupported[n]=1
  bad=1
}
function trim(s) { sub(/^[ \t]+/, "", s); sub(/[ \t]+$/, "", s); return s }
function unquote(s) {
  s=trim(s)
  if (s ~ /^".*"$/ || s ~ /^\047.*\047$/) s=substr(s,2,length(s)-2)
  return s
}
function replace_literal(s, old, value, p, result) {
  result=""
  while ((p=index(s,old)) > 0) {
    result=result substr(s,1,p-1) value
    s=substr(s,p+length(old))
  }
  return result s
}
function resolve(s, k,t) {
  resolved_escape=0
  # Preserve YAML escape provenance even if conflicting assignments invalidate
  # the value. Only a reference that reaches an inspected statement fires.
  for (k in escaped_scalars) {
    t=replace_literal(s,"${" k "}","")
    t=replace_literal(t,"${{ env." k " }}","")
    t=replace_variable(t,k,"")
    if (t!=s) resolved_escape=1
  }
  for (k in vars) {
    s=replace_literal(s,"${" k "}",vars[k])
    s=replace_literal(s,"${{ env." k " }}",vars[k])
    # Match an entire shell variable; $PATH must not rewrite $PATH_SUFFIX.
    s=replace_variable(s,k,vars[k])
  }
  return s
}
function replace_variable(s,k,v, p,t,nextchar,out) {
  out=""
  while ((p=index(s,"$" k)) > 0) {
    nextchar=substr(s,p+length(k)+1,1)
    t=substr(s,1,p-1)
    if (nextchar ~ /[A-Za-z_0-9]/) {
      out=out t "$" k; s=substr(s,p+length(k)+1)
    } else {
      out=out t v; s=substr(s,p+length(k)+1)
    }
  }
  return out s
}
# Dispatcher grammar: options taking a separate argument are explicit below;
# attached short values and --long=value consume only their own word.
# Unknown wrappers carrying gh/curl fail closed instead of guessing execution.
function dispatch_options(cmd,opt) {
  if (cmd=="xargs") return opt ~ /^(-[aIEnLsPd]|--(replace|eof|max-args|max-lines|max-chars|max-procs|delimiter|arg-file))$/
  if (cmd=="env") return opt ~ /^(-[uCS]|--(unset|chdir|split-string))$/
  if (cmd=="exec") return opt=="-a"
  if (cmd=="nice") return opt ~ /^(-n|--adjustment)$/
  if (cmd=="timeout") return opt ~ /^(-[ks]|--(kill-after|signal))$/
  if (cmd=="sudo") return opt ~ /^(-[ugpchrtTDCR]|--(user|group|prompt|close-from|host|role|type|chdir|chroot|command-timeout))$/
  if (cmd=="time") return opt ~ /^(-[fo]|--(format|output))$/
  return 0
}
# Word values plus source offsets let direct requests retain quoting and bundle
# provenance. Shell strings are decoded exactly one quoting layer at dispatch.
function shell_words(s,w,offset, j,ch,q,escaped,word,total,beg) {
  for (j=1;j<=length(s)+1;j++) {
    ch=substr(s,j,1)
    if (!beg && j<=length(s) && ch !~ /[ \t]/) beg=j
    if (escaped) {
      if (q=="\"" && ch !~ /[\\"$`]/) word=word "\\"
      word=word ch; escaped=0; continue
    }
    if (ch=="\\" && q!="\047") { escaped=1; continue }
    if (ch=="\047" || ch=="\"") {
      if (q=="") { q=ch; continue }
      if (q==ch) { q=""; continue }
    }
    if (j>length(s) || (q=="" && ch ~ /[ \t]/)) {
      if (beg) { w[++total]=word; offset[total]=beg }
      word=""; beg=0
    } else word=word ch
  }
  return total
}
function carries_request(s, w,offset,total,j) {
  total=shell_words(s,w,offset)
  for (j=1;j<=total;j++) if (w[j] ~ /(^|[^A-Za-z_])(gh|curl)([^A-Za-z_]|$)/) return 1
  return 0
}
function scan_commands(s,n,depth, j,ch,q,escaped,segment,piped,previous) {
  if (depth>16) { hit("b",n,"dispatch nesting cannot be proven"); return }
  for (j=1;j<=length(s)+1;j++) {
    ch=substr(s,j,1)
    if (!escaped && (ch=="\047" || ch=="\"")) {
      if (q=="") q=ch
      else if (q==ch) q=""
    }
    if (j>length(s) || (!escaped && q=="" && (ch==";" || ch=="|" || ch=="&" || ch=="\n"))) {
      dispatch(segment,n,depth,piped ? previous : "")
      previous=(piped ? previous " | " : "") segment; segment=""; piped=(ch=="|" && substr(s,j+1,1)!="|")
      if (substr(s,j,2)=="||" || substr(s,j,2)=="&&") j++
    } else segment=segment ch
    if (ch=="\\" && !escaped && q!="\047") escaped=1
    else escaped=0
  }
}
function dispatch(s,n,depth,input, w,offset,total,j,k,cmd,t,body,resolved) {
  s=trim(s)
  if (s=="" || s ~ /^#/) return
  # Rule d already rejects undecodable YAML. Preserve its legacy diagnostics.
  if (unsupported[n]) { inspect(s,n); return }
  resolved=resolve(s)
  if (resolved_escape && s !~ /^(-[ \t]+)?[A-Za-z_][A-Za-z_0-9-]*:[ \t]/) hit("d",n,"escaped collected scalar reaches run in decide")
  total=shell_words(resolved,w,offset); j=1
  while (j<=total) {
    cmd=w[j]; sub(/^.*\//,"",cmd)
    if (cmd=="gh" || cmd=="curl") {
      # Canonicalize executable words after quote removal (g""h, /bin/curl),
      # but preserve every argument byte for the request/bundle parser.
      if (cmd=="gh" && w[j+1]=="api") {
        inspect("gh api " (j+2<=total ? substr(resolved,offset[j+2]) : ""),n)
      } else if (cmd=="curl") inspect("curl " (j+1<=total ? substr(resolved,offset[j+1]) : ""),n)
      return
    }
    if (cmd=="sh" || cmd=="bash" || cmd=="eval") {
      if (cmd=="eval") {
        body=""; for (k=j+1;k<=total;k++) body=body (k==j+1 ? "" : " ") w[k]
        scan_commands(body,n,depth+1); return
      }
      for (k=j+1;k<=total;k++) {
        if (w[k] ~ /^-[^-]*c/) { scan_commands(w[k+1],n,depth+1); return }
      }
      if (input!="") {
        # A pipe supplies executable text, not inert echo/printf arguments.
        # Its formatting/expansion is not generally provable statically.
        if (carries_request(input)) hit("b",n,"dispatch through shell stdin")
      }
      break
    }
    if (cmd ~ /^(xargs|env|command|exec|nice|nohup|timeout|sudo|time)$/) {
      j++
      while (j<=total && w[j] ~ /^-/) {
        t=w[j++]
        if (t=="--") break
        if (dispatch_options(cmd,t)) j++
      }
      if (cmd=="env") while (j<=total && w[j] ~ /^[A-Za-z_][A-Za-z_0-9]*=/) j++
      if (cmd=="timeout") j++
      if (cmd=="xargs" && carries_request(input)) hit("b",n,"dispatch through xargs stdin")
      continue
    }
    if (w[j] ~ /^[A-Za-z_][A-Za-z_0-9]*=/ && j<total) { j++; continue }
    # Shell syntax/assignments already supported by the conservative scanner
    # retain their original analysis, including command substitutions.
    if (s ~ /^(-[ \t]+)?[A-Za-z_][A-Za-z_0-9-]*:/ ||
        s ~ /^[A-Za-z_][A-Za-z_0-9]*=/ || cmd ~ /^(if|then|elif|else|while|do|done|return|local)$/) { inspect(s,n); return }
    if (cmd=="echo" || cmd=="printf") {
      if (s ~ /[$][(]|`/) inspect(s,n)
      return
    }
    break
  }
  if (carries_request(resolved)) {
    hit("b",n,"dispatch cannot be proven")
    inspect(s,n)
  }
}
function inspect(s,n, gh,curl,explicit,implicit,get,write,path,tail,facts,unresolved,query_read,request_source) {
  request_source=s
  # Field-only provenance constrains option shape, not GraphQL operation values.
  # Include every possible append before resolving variables or checking writes.
  if (field_vectors[n]) s=replace_literal(s,"\"$@\"",field_values[n])
  s=resolve(s)
  if (resolved_escape && request_source !~ /^(-[ \t]+)?[A-Za-z_][A-Za-z_0-9-]*:[ \t]/) hit("d",n,"escaped collected scalar reaches run in decide")
  gh=(s ~ /(^|[^A-Za-z_])gh[ \t]+api([ \t]|$)/)
  curl=(s ~ /(^|[^A-Za-z_])curl([ \t]|$)/)
  if (!gh && !curl) return
  # Preserve bundle boundaries for option-argument consumption checks.
  request(resolve(request_source),gh,facts,field_vectors[n],escaped_runs[n])
  if (gh && s ~ /query[=]["\047]*@/) facts["method_unknown"]=1
  unresolved=facts["method_unknown"]
  explicit=facts["write"]
  get=facts["method_seen"] && !facts["non_get"]
  implicit=facts["implicit"]
  query_read=0
  write=explicit || unresolved || (implicit && !get)
  # GraphQL query transport uses POST; the operation, not transport, decides.
  if (gh && s ~ /api[ \t]+graphql([ \t]|$)/ && s !~ /(^|[^A-Za-z_])mutation([^A-Za-z_]|$)/) {
    if (s ~ /query[= \t]+["\047]*query([ \t({]|$)/ || s ~ /query[= \t]+["\047]*\{/) { write=unresolved; query_read=1 }
    else if (implicit) hit("b",n,"GraphQL operation cannot be proven read-only")
  }
  # No write signal means a read, even when its endpoint is dynamic.
  # Only literal PUT/DELETE may use the contract-defined variable ledger tail.
  if (unresolved || (write && facts["target_unknown"] &&
      (!facts["method_seen"] || !facts["ledger_only"] || facts["non_ledger_method"]))) hit("b",n,"unresolvable gh/curl target in decide")
  if (s ~ /(^|[^A-Za-z_])mutation([^A-Za-z_]|$)/) hit("b",n,"GraphQL mutation in decide")
  if (write && (s ~ /\/(collaborators|invitations|comments|graphql)([^A-Za-z_-]|$)|\/contents\/SUPPORTERS[.]md/ || (gh && s ~ /api[ \t]+graphql([ \t]|$)/))) hit("b",n,"write to delivery endpoint")
  if (write && facts["contents_bad"]) hit("a-prime",n,"Contents write outside provable ledger/ prefix")
  if (write && match(s,/\/contents\//)) {
    tail=substr(s,RSTART+RLENGTH)
    # Traversal and encoding must not turn the allowlisted prefix into escape.
    if (tail !~ /^ledger\// || tail ~ /(^|\/)\.\.([\/"\047? \t]|$)|%2[eEfF]|%5[cC]/) hit("a-prime",n,"Contents write outside provable ledger/ prefix")
  }
}
# Inspect actual endpoint words, never a ledger-looking header or payload.
function target(t,facts, path,tail,literal) {
  if (match(t,/\/contents\//)) {
    tail=substr(t,RSTART+RLENGTH)
    if (tail !~ /^ledger\// || tail ~ /[.][.]|%2[eEfF]|%5[cC]/) facts["contents_bad"]=1
  }
  if (t !~ /[$`]/) return
  facts["target_unknown"]=1
  path=t
  sub(/^https:\/\/api[.]github[.]com\//,"",path)
  sub(/^\//,"",path)
  if (match(path,/^repos\/(OPAQUE_CONTEXT_[0-9]+|[^\/$`]+\/[^\/$`]+)\/contents\/ledger\//)) {
    tail=substr(path,RLENGTH+1)
    # A variable filename is allowed only after the complete literal prefix.
    # Reject literal traversal/encoding and nested directories in that tail.
    if (tail ~ /[$][{]?[A-Za-z_][A-Za-z_0-9]*[}]?/ &&
        tail !~ /[.][.]|%2[eEfF]|%5[cC]|\/|`|[$][(]/) {
      literal=tail
      gsub(/[$][{][A-Za-z_][A-Za-z_0-9]*[}]|[$][A-Za-z_][A-Za-z_0-9]*/,"",literal)
      if (literal !~ /[$`{}]/) return
    }
  }
  facts["ledger_only"]=0
}
# Assignments are collected before any invocation is inspected. Conflicts and
# dynamic assignments permanently invalidate a name, independent of key order.
function collect(key,value,yaml, expression,token) {
  if (yaml && trim(value) ~ /^"/ && index(value,"\\")) escaped_scalars[key]=1
  value=unquote(value)
  while (match(value,/\$\{\{[ \t]*(inputs|github|secrets|vars)[.][A-Za-z_0-9.]+[ \t]*\}\}/)) {
    expression=substr(value,RSTART,RLENGTH)
    if (!(expression in opaque)) opaque[expression]="OPAQUE_CONTEXT_" ++opaque_count
    token=opaque[expression]
    value=substr(value,1,RSTART-1) token substr(value,RSTART+RLENGTH)
  }
  if (value ~ /[$`]/ || (key in vars && vars[key]!=value)) invalid[key]=1
  if (invalid[key]) delete vars[key]
  else vars[key]=value
}
function process(s,n,key,value) {
  s=trim(s)
  if (s ~ /^[A-Za-z_][A-Za-z_0-9]*:[ \t]+/) {
    key=s; sub(/:.*/,"",key)
    value=s; sub(/^[^:]*:[ \t]+/,"",value)
    if (key !~ /^(run|if|name|uses)$/) collect(key,value,1)
  } else if (s ~ /^[A-Za-z_][A-Za-z_0-9]*=/) {
    key=s; sub(/=.*/,"",key)
    value=s; sub(/^[^=]*=/,"",value)
    collect(key,value)
  }
}
# Read shell words without splitting quoted option values (headers, payloads).
# Classify method options separately from header/payload option arguments.
# Only positional targets and --url values participate in target resolution.
function bundle(s, j,ch,q,escaped) {
  for (j=1;j<=length(s);j++) {
    ch=substr(s,j,1)
    if (escaped) { escaped=0; continue }
    if (ch=="\\" && q!="\047") { escaped=1; continue }
    if (ch=="\047" || ch=="\"") {
      if (q=="") q=ch
      else if (q==ch) q=""
    }
    if (ch=="$" && q!="\047" && substr(s,j) ~ /^[$]([@*]|[{]([@*]([}:])|[^}]*\[[^]]*\][^}]*[}]))/) return 1
  }
  return 0
}
function request(s,gh,facts,fields,escaped_scalar, words,raw_words,field_word,raw,total,j,ch,q,escaped,word,t,skip,method,target_seen,pos,opt,arg,short_value) {
  if (gh) sub(/^.*gh[ \t]+api[ \t]+/,"",s)
  else sub(/^.*curl[ \t]+/,"",s)
  facts["ledger_only"]=1
  total=0; word=""; q=""; escaped=0
  for (j=1;j<=length(s)+1;j++) {
    ch=substr(s,j,1)
    if (j<=length(s) && (q!="" || ch !~ /[ \t]/ || escaped)) raw=raw ch
    if (escaped) { word=word ch; escaped=0; continue }
    if (ch=="\\" && q!="\047") { escaped=1; continue }
    if (ch=="\047" || ch=="\"") {
      if (q=="") { q=ch; continue }
      if (q==ch) { q=""; continue }
    }
    if (j>length(s) || (q=="" && ch ~ /[ \t]/)) {
      if (word!="") { words[++total]=word; raw_words[total]=raw }
      word=""; raw=""
    } else word=word ch
  }
  # A bundle can supply extra options even when its first word is a payload,
  # header, method, or URL argument. Check before consuming option arguments.
  for (j=1;j<=total;j++) {
    if (bundle(raw_words[j])) {
      if (gh && fields && raw_words[j]=="\"$@\"") field_word[j]=1
      else facts["method_unknown"]=1
    }
  }
  for (j=1;j<=total;j++) {
    t=words[j]
    if (t ~ /^[|&]/) break
    # Redirections may precede method flags in the same invocation.
    if (t ~ /^[0-9]*[<>]+$/) {
      if (field_word[++j]) facts["method_unknown"]=1
      continue
    }
    if (t ~ /^[0-9]*[<>]/) continue
    if (skip) {
      if (field_word[j]) facts["method_unknown"]=1
      skip=0; continue
    }
    # Field-pair provenance only holds at an option boundary. Consuming its
    # first -f as a header/value would expose the next word as an option.
    if (field_word[j]) facts["implicit"]=1
    if (t ~ /[$]([0-9]|[{][0-9]+[}])/) facts["method_unknown"]=1
    if (!gh && t ~ /^--(form|form-string|config)(=|$)/) facts["method_unknown"]=1
    method=""
    short_value=0
    if (!gh && t ~ /^-[^-]/) {
      # curl clusters stop at the first option taking an argument. Its suffix
      # is the value, even when that suffix looks like another option letter.
      # gh api has individual short flags, not curl-style cluster syntax.
      for (pos=2;pos<=length(t);pos++) {
        opt=substr(t,pos,1)
        if (index("XdTFKHuoweAbcEmrxyzCDYUPQht",opt)) {
          arg=substr(t,pos+1)
          if (arg=="") arg=words[++j]
          if (arg=="" || field_word[j]) facts["method_unknown"]=1
          if (opt=="X") { method=arg; short_value=1 }
          else if (opt=="d" || opt=="T" || opt=="F") facts["implicit"]=1
          # Multipart and external configuration remain fail-closed even if
          # another option explicitly selects GET (the existing R4 contract).
          if (opt=="F" || opt=="K" || opt=="Q") facts["method_unknown"]=1
          break
        }
        if (!index("012346#sSfikvjVLIOJNGgqRaBlnpZM",opt)) facts["method_unknown"]=1
      }
      if (!short_value) continue
    }
    if (short_value) { method=arg }
    else if (t=="-X" || (gh && t=="--method") || (!gh && t=="--request")) method=words[++j]
    else if (t ~ /^-X./) method=substr(t,3)
    else if (gh && t ~ /^--method=/) method=substr(t,10)
    else if (!gh && t ~ /^--request=/) method=substr(t,11)
    else if (t=="--url" && !gh) {
      target(words[++j],facts)
      if (field_word[j]) facts["method_unknown"]=1
      continue
    } else if (t ~ /^--url=/ && !gh) {
      target(substr(t,7),facts)
      continue
    } else {
      if ((gh && t ~ /^(-[fF]|--(input|raw-field|field)(=|$))/) || (!gh && t ~ /^(-[dT]|--(data|data-raw|data-binary|data-urlencode|json|upload-file)(=|$))/)) facts["implicit"]=1
      if ((gh && t ~ /^(-H|--header|-f|-F|--field|--raw-field|--input|--hostname|--jq|-q|--template|-t|--cache|-p|--preview)$/) || (!gh && t ~ /^(-H|--header|-F|--form|--form-string|-d|-T|--data|--data-raw|--data-binary|--data-urlencode|--json|--upload-file|-o|--output|-w|--write-out|--connect-timeout|--max-time|-u|--user|-A|--user-agent|-e|--referer)$/)) { skip=1; continue }
      if (t ~ /^-/) continue
      if (!gh || !target_seen) {
        target(t,facts)
        target_seen=1
      }
      continue
    }
    if (field_word[j]) facts["method_unknown"]=1
    method=toupper(method)
    facts["method_seen"]=1
    if (method!="GET") facts["non_get"]=1
    if (method!="PUT" && method!="DELETE") facts["non_ledger_method"]=1
    # Raw escaped YAML is already rejected by d; preserve its prior diagnostics
    # rather than treating undecoded escape text as a newly invalid method.
    if (method=="" || method ~ /[$`]|OPAQUE_CONTEXT_/ ||
        (!escaped_scalar && method !~ /^(GET|HEAD|OPTIONS|TRACE|CONNECT|PUT|POST|PATCH|DELETE)$/)) facts["method_unknown"]=1
    if (method ~ /^(PUT|POST|PATCH|DELETE)$/) facts["write"]=1
  }
}

# A deliberately small provenance grammar for field-only argument builders.
# Proof starts at a function boundary and an unconditional empty reset. Before
# the reset, only local declarations and a single-line return guard are allowed.
# Afterwards only jq/read plumbing and quoted -f/-F pair appends preserve it.
# Anything else (including calls, eval, shift, another reset, or scope exit)
# discards the proof. No endpoint or function name earns an exemption.
function field_builder(s,n, append,plumbing,invocation) {
  s=trim(s)
  if (s=="" || s ~ /^#/) return
  if (s ~ /^[A-Za-z_][A-Za-z_0-9]*[ \t]*\(\)[ \t]*\{[ \t]*$/) {
    field_prefix=1; field_safe=0; field_appends=""; return
  }
  if (field_prefix) {
    if (s=="set --") { field_prefix=0; field_safe=1; return }
    if (s ~ /^local [A-Za-z_]/ && s !~ /[;`{}]|[$][(]/) return
    if (s ~ /^case "[^"`]+" in [A-Za-z_0-9*]+\) ;; \*\) return [0-9]+ ;; esac$/) return
    field_prefix=0
  }
  if (!field_safe) return
  if (s ~ /^gh[ \t]+api[ \t]/) {
    invocation=s
    sub(/[ \t]+\|\|[ \t]+return[ \t]+[0-9]+[ \t]*$/,"",invocation)
    if (invocation !~ /[;|&`]|[$][(]/) {
      field_vectors[n]=1
      field_values[n]=field_appends
    }
    field_safe=0; return
  }
  append="set -- \"\\$@\" -[fF] \"[^\"`]*=[^\"`]*\""
  if (s ~ ("^" append "$") ||
      s ~ ("^if \\[ [^][;`&|]+ \\]; then " append "$") ||
      s ~ ("^else " append "; fi$")) {
    plumbing=s
    sub(/^.*set -- "[$]@" /,"",plumbing)
    sub(/; fi$/,"",plumbing)
    if (s !~ /[$][(]/ && !bundle(plumbing)) {
      field_appends=field_appends " " plumbing
      return
    }
  }
  if (s ~ /^while IFS= read -r [A-Za-z_][A-Za-z_0-9]*; do$/) return
  if (s ~ /^[A-Za-z_][A-Za-z_0-9]*=\$\(jq [^;`]*\)$/ || s ~ /^done < <\(jq [^;`]*\)$/) {
    plumbing=s
    sub(/^[^(]*\(/,"",plumbing); sub(/\)$/,"",plumbing)
    if (plumbing !~ /[()&]/) return
  }
  field_safe=0
}

# Workflow-level env is outside the decide slice but participates in shell
# expansion there. Collect only its mapping entries, including a name key.
/^env:[ \t]*(#.*)?$/ { workflow_env=1; next }
workflow_env {
  if ($0 ~ /^[ \t]*(#.*)?$/) next
  if ($0 ~ /^[^ \t]/) workflow_env=0
  else {
    mapping=trim($0)
    if (mapping ~ /^[A-Za-z_][A-Za-z_0-9]*:[ \t]+/) {
      key=mapping; sub(/:.*/,"",key)
      value=mapping; sub(/^[^:]*:[ \t]+/,"",value)
      collect(key,value,1)
    }
    next
  }
}
/^[ \t]*decide:[ \t]*(#.*)?$/ {
  if (inside) hit("structure",NR,"duplicate decide job")
  inside=1; found=1; indent=match($0,/[^ \t]/)-1
  next
}
inside {
  depth=match($0,/[^ \t]/)-1
  if ($0 !~ /^[ \t]*(#.*)?$/ && depth<=indent) inside=0
  if (!inside) next
  lines[++count]=$0; numbers[count]=NR
}
END {
  if (!found) { hit("structure",1,"decide job missing"); exit 1 }
  command=""; start=0; quote=""
  for (i=1;i<=count;i++) {
    line=lines[i]
    if (line ~ /SUPPORTER_LOOP_TOKEN|TELEGRAM_[A-Za-z_0-9]*|api[.]telegram[.]org/) hit("a",numbers[i],"forbidden credential or Telegram host")
    if (line ~ /addDiscussionComment/) hit("c",numbers[i],"discussion comment mutation name")
    if (line ~ /^[ \t]*#/) continue
    if (trim(line)=="") continue
    # Literal blocks preserve shell lines: do not parse their body as YAML.
    depth=match(line,/[^ \t]/)-1
    if (literal && trim(line)!="" && depth<=literal_depth) literal=0
    body_literal=literal
    if (literal) field_builder(line,numbers[i])
    else { field_prefix=0; field_safe=0 }
    if (!literal) {
      if (line ~ /(:[ \t]+|^[ \t]*-[ \t]+)([!&][^ \t]+[ \t]+)*>[0-9+-]*[ \t]*(#.*)?$/) hit("d",numbers[i],"multi-line non-literal scalar in decide is not scannable")
      mapping=trim(line)
      sequence=(mapping ~ /^-[ \t]+/)
      key_depth=depth
      if (mapping ~ /^-[ \t]+/) {
        match(mapping,/^-[ \t]+/)
        key_depth+=RLENGTH
        mapping=substr(mapping,RLENGTH+1)
      }
      # Track YAML ancestry, including indentless sequences, without treating
      # defaults.run (a mapping) as a step run (an executable scalar).
      parent=""; parent_depth=-1
      for (level in keys) {
        if (level+0>=key_depth) delete keys[level]
        else if (level+0>parent_depth) { parent_depth=level; parent=keys[level] }
      }
      under_with=0
      for (level in keys) if (keys[level]=="with") under_with=1
      scalar_sequence=sequence && parent!="steps" && parent!="run" && parent!="if" && parent!=""
      # Outside literal bodies, only plain mapping keys are scannable.
      if (!scalar_sequence && mapping!="" && mapping !~ /^[A-Za-z_][A-Za-z_0-9-]*:( |$)/) {
        hit("d",numbers[i],"non-plain key or flow mapping in decide is not scannable")
      }
      if (mapping ~ /^[A-Za-z_][A-Za-z_0-9-]*:( |$)/) {
        key=mapping; sub(/:.*/,"",key)
        value=mapping; sub(/^[^:]*:[ \t]*/,"",value)
        keys[key_depth]=key
        # with.script / with.run are executable inputs (github-script and
        # run-wrapper actions). Scan these for every action, including dynamic
        # uses values, so action-name aliases cannot bypass the boundary.
        with_exec=under_with && parent=="with" && key ~ /^(script|run)$/
        executable_run=(key=="run" && !under_with) || with_exec
        data_value=under_with && !with_exec
        literal_data=data_value
        if (parent=="env" || parent=="with") collect(key,value,1)
        if (executable_run && parent!="defaults" && value ~ /^!/) hit("d",numbers[i],"tagged run scalar in decide is not scannable")
        if (value ~ /^[*&]/) hit("d",numbers[i],"alias or anchor in decide is not scannable")
        if (value ~ /^[{\[]/) hit("d",numbers[i],"non-plain key or flow mapping in decide is not scannable")
        # Strip YAML tags before recognizing scalar styles.
        sub(/^(![^ \t]+[ \t]+)+/,"",value)
        if (value ~ /^[*&]/) hit("d",numbers[i],"alias or anchor in decide is not scannable")
        next_line=i+1
        while (next_line<=count && lines[next_line] ~ /^[ \t]*$/) next_line++
        deeper=(next_line<=count && match(lines[next_line],/[^ \t]/)-1>key_depth)
        if ((value=="" || value ~ /^#/) && deeper) {
          following=trim(lines[next_line])
          if (following ~ /^\|[0-9+-]*[ \t]*(#.*)?$/) {
            literal=1; literal_depth=key_depth
          } else if ((executable_run && parent!="defaults") || key=="if" || (following !~ /^-[ ]+/ && following !~ /^[A-Za-z_][A-Za-z_0-9-]*:( |$)/)) {
            hit("d",numbers[i],"multi-line non-literal scalar in decide is not scannable")
          }
        }
        if (value ~ /^\|[0-9+-]*[ \t]*(#.*)?$/) {
          literal=1; literal_depth=key_depth
        } else if (value!="" && value !~ /^#/) {
          multiline=0
          if (deeper) multiline=1
          first=substr(value,1,1)
          if (first=="\"" || first=="\047") {
            closed=0
            for (j=2;j<=length(value);j++) {
              ch=substr(value,j,1)
              if (first=="\"" && ch=="\\") {
                if (executable_run) {
                  hit("d",numbers[i],"escaped run scalar in decide is not scannable")
                  escaped_runs[numbers[i]]=1
                }
                j++; continue
              }
              if (ch==first) {
                if (first=="\047" && substr(value,j+1,1)==first) { j++; continue }
                closed=1; break
              }
            }
            if (!closed) multiline=1
          }
          if (multiline) hit("d",numbers[i],"multi-line non-literal scalar in decide is not scannable")
        }
      }
    }
    if ((body_literal && literal_data) || (!body_literal && data_value)) {
      data_statements[++data_count]=line; data_lines[data_count]=numbers[i]
      continue
    }
    if (command=="") start=numbers[i]
    t=trim(line)
    sub(/^- run:[ \t]*/,"",t)
    sub(/^run:[ \t]*/,"",t)
    if (!body_literal && with_exec) sub(/^(script|run):[ \t]*/,"",t)
    if (!body_literal && (key=="run" || with_exec) && !unsupported[numbers[i]]) t=unquote(t)
    command=command (join_token ? "" : " ") t
    join_token=0
    # Track shell quotes to keep multiline GraphQL operations one invocation.
    escaped=0
    for (c=1;c<=length(t);c++) {
      ch=substr(t,c,1)
      if (escaped) { escaped=0; continue }
      if (ch=="\\" && quote!="\047") { escaped=1; continue }
      if (quote=="") {
        if (ch=="\047" || ch=="\"") quote=ch
      } else if (ch==quote) quote=""
    }
    if (command ~ /\\[ \t]*$/) {
      # Shell continuation removes both characters inside a word. Whitespace
      # before the backslash remains a word separator (the idiomatic form).
      match(command,/\\[ \t]*$/)
      join_token=(RSTART>1 && substr(command,RSTART-1,1) !~ /[ \t]/)
      sub(/\\[ \t]*$/,"",command); continue
    }
    if (quote!="") continue
    # A pipe/control operator also continues a shell command across a literal
    # block newline; retain upstream text until its consumer is available.
    if (body_literal && command ~ /([|]|&&)[ \t]*$/) continue
    # Separate simple statements outside quotes for the collection pass.
    segment=""; q=""; escaped=0
    for (c=1;c<=length(command);c++) {
      ch=substr(command,c,1)
      if (!escaped && (ch=="\047" || ch=="\"")) {
        if (q=="") q=ch
        else if (q==ch) q=""
      }
      if (q=="" && (ch==";" || ch=="|" || substr(command,c,2)=="&&")) {
        process(segment,start); segment=""
        if (substr(command,c,2)=="&&" || substr(command,c,2)=="||") c++
      } else segment=segment ch
      if (ch=="\\" && !escaped && q!="\047") escaped=1
      else escaped=0
    }
    process(segment,start)
    statements[++statement_count]=command; statement_lines[statement_count]=start
    command=""
  }
  if (command!="") hit("structure",start,"unterminated command or quote")
  data_only=1
  for (i=1;i<=data_count;i++) inspect(data_statements[i],data_lines[i])
  data_only=0
  for (i=1;i<=statement_count;i++) scan_commands(statements[i],statement_lines[i],0)
  exit bad ? 1 : 0
}
' "$1"
