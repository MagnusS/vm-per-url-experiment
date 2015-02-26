open Mirage

let fs = crunch "./htdocs"

let ipv4_config =
      let address = Ipaddr.V4.of_string_exn "%IP%" in
      let netmask = Ipaddr.V4.of_string_exn "%NETMASK%" in
      let gateways = [Ipaddr.V4.of_string_exn "%GATEWAY%"] in
      { address; netmask; gateways }

let stack console = direct_stackv4_with_static_ipv4 console tap0 ipv4_config

let server =
	conduit_direct (stack default_console)

let http_srv =
  let mode = `TCP (`Port 80) in
  http_server mode server

let main =
  foreign "Dispatch.Main" (console @-> kv_ro @-> http @-> job)

let () =
  add_to_ocamlfind_libraries ["re.str"];
  add_to_opam_packages ["re"];

  register "www" [
    main $ default_console $ fs $ http_srv
  ]
