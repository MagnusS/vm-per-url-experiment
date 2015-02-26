(* Copyright (c) 2015 Magnus Skjegstad <magnus@skjegstad.com>
 *
 * Permission to use, copy, modify, and distribute this software for any
 * purpose with or without fee is hereby granted, provided that the above
 * copyright notice and this permission notice appear in all copies.
 *
 * THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
 * WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
 * MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
 * ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
 * WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
 * ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
 * OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
 *)

open Dns
open Lwt

let forward_resolve resolver _class _type _name =
    Printf.printf "Forwarding query for %s\n%!" (Name.domain_name_to_string _name);
    Dns_resolver_unix.resolve resolver _class _type _name >>= fun result ->
    return (Some (Dns.Query.answer_of_response result ))

let match_or_forward resolver zone ~src ~dst packet =
    let open Packet in
    match packet.questions with
    | [] -> Lwt.return_none (* no questions, return none *)
    | [q] -> begin (* one question, try zone first *)
                zone ~src ~dst packet >>= fun zone_answer ->
                match zone_answer with
                | None -> forward_resolve resolver q.q_class q.q_type q.q_name (* no result from zone, just forward *)
                | Some answer -> begin (* got answer, check return code *)
                    match answer.Query.rcode with
                    | Packet.NoError -> Printf.printf "Local match for %s\n%!" (Name.domain_name_to_string q.q_name);
                                        return (Some answer)
                    | _ -> forward_resolve resolver q.q_class q.q_type q.q_name
                end
    end
    | _::_::_ -> Lwt.return_none (* multiple questions? too much for us... *)

let () =
    Lwt_main.run (
        (* server address and port *)
        let address = "0.0.0.0" in
        let port = 53 in
        (* create forward resolver using /etc/resolv.conf *)
        Dns_resolver_unix.create () >>= fun resolver ->
        (* process zone file *)
        Dns_server_unix.eventual_process_of_zonefiles ["www.skjegstad.com.zone"] >>= fun zone ->
        (* check db first, then fall back to resolver on error *)
        let processor = (Dns_server.processor_of_process (match_or_forward resolver zone) :> (module Dns_server.PROCESSOR)) in
        Printf.printf "DNS server now running at %s port %d...\n%!" address port;
        Dns_server_unix.serve_with_processor ~address ~port ~processor
    )
