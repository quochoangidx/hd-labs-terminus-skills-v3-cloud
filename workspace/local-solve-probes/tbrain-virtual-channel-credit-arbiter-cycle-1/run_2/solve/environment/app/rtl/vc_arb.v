// vc_arb: three-channel credit-based link transmit arbiter.
// Behaviour is defined in /app/docs/spec.md.
module vc_arb (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [2:0]  in_valid,
    input  wire [23:0] in_data,
    output wire [2:0]  in_ready,
    output reg         out_valid,
    output reg  [1:0]  out_vc,
    output reg  [7:0]  out_data,
    input  wire        out_ready,
    input  wire [2:0]  cr_ret,
    input  wire [2:0]  flush,
    input  wire        cfg_we,
    input  wire [1:0]  cfg_vc,
    input  wire [2:0]  cfg_credits,
    output wire [8:0]  credits
);

    // ------------------------------------------------------------------
    // State (section 2)
    // ------------------------------------------------------------------
    reg [23:0] b0_r;     // oldest byte per VC, bits 8v+7:8v
    reg [23:0] b1_r;     // newest byte per VC (valid when cnt==2)
    reg [5:0]  cnt_r;    // bits 2v+1:2v -> cnt[v], 0..2
    reg [8:0]  cred_r;   // bits 3v+2:3v -> cred[v], 0..7
    reg [1:0]  last_r;   // VC of the most recent grant
    reg [1:0]  run_r;    // 1 or 2

    wire [1:0] cnt0 = cnt_r[1:0];
    wire [1:0] cnt1 = cnt_r[3:2];
    wire [1:0] cnt2 = cnt_r[5:4];
    wire [2:0] cred0 = cred_r[2:0];
    wire [2:0] cred1 = cred_r[5:3];
    wire [2:0] cred2 = cred_r[8:6];

    // ------------------------------------------------------------------
    // Outputs (section 3): registers only
    // ------------------------------------------------------------------
    assign in_ready = {(cnt2 < 2'd2), (cnt1 < 2'd2), (cnt0 < 2'd2)};
    assign credits  = cred_r;

    // ------------------------------------------------------------------
    // Eligibility (4.2) and opportunity (4.1)
    // ------------------------------------------------------------------
    wire [2:0] elig;
    assign elig[0] = (cnt0 != 2'd0) && (cred0 != 3'd0) && (flush[0] == 1'b0);
    assign elig[1] = (cnt1 != 2'd0) && (cred1 != 3'd0) && (flush[1] == 1'b0);
    assign elig[2] = (cnt2 != 2'd0) && (cred2 != 3'd0) && (flush[2] == 1'b0);

    wire opp = (out_valid == 1'b0) || (out_ready == 1'b1);

    // last is always 0..2; guard the round-robin order anyway.
    wire [1:0] cand1 = (last_r == 2'd0) ? 2'd1 : ((last_r == 2'd1) ? 2'd2 : 2'd0);
    wire [1:0] cand2 = (last_r == 2'd0) ? 2'd2 : ((last_r == 2'd1) ? 2'd0 : 2'd1);
    wire [1:0] cand3 = (last_r > 2'd2) ? 2'd0 : last_r;

    wire elig_last = (last_r == 2'd0) ? elig[0]
                   : (last_r == 2'd1) ? elig[1]
                   : (last_r == 2'd2) ? elig[2] : 1'b0;

    function [0:0] elig_of;
        input [2:0] e;
        input [1:0] v;
        begin
            elig_of = (v == 2'd0) ? e[0] : (v == 2'd1) ? e[1] : (v == 2'd2) ? e[2] : 1'b0;
        end
    endfunction

    // ------------------------------------------------------------------
    // Selection (4.3)
    // ------------------------------------------------------------------
    reg        grant;
    reg [1:0]  gvc;
    reg        keep_run;   // the "run continues" branch was taken

    always @* begin
        grant    = 1'b0;
        gvc      = 2'd0;
        keep_run = 1'b0;
        if (opp) begin
            if ((run_r == 2'd1) && elig_last) begin
                grant    = 1'b1;
                gvc      = last_r;
                keep_run = 1'b1;
            end else if (elig_of(elig, cand1)) begin
                grant = 1'b1;
                gvc   = cand1;
            end else if (elig_of(elig, cand2)) begin
                grant = 1'b1;
                gvc   = cand2;
            end else if (elig_of(elig, cand3)) begin
                grant = 1'b1;
                gvc   = cand3;
            end
        end
    end

    wire [2:0] grant_v = grant ? (3'b001 << gvc) : 3'b000;

    wire [1:0] next_last = grant ? gvc : last_r;
    wire [1:0] next_run  = grant ? (keep_run ? 2'd2 : 2'd1)
                                 : (((flush[0] && (last_r == 2'd0)) ||
                                     (flush[1] && (last_r == 2'd1)) ||
                                     (flush[2] && (last_r == 2'd2))) ? 2'd2 : run_r);

    // Oldest byte of the granted VC
    wire [7:0] gdata = (gvc == 2'd0) ? b0_r[7:0]
                     : (gvc == 2'd1) ? b0_r[15:8] : b0_r[23:16];

    // ------------------------------------------------------------------
    // Shared registers
    // ------------------------------------------------------------------
    always @(posedge clk) begin
        if (!rst_n) begin
            out_valid <= 1'b0;
            out_vc    <= 2'd0;
            out_data  <= 8'd0;
            last_r    <= 2'd2;
            run_r     <= 2'd2;
        end else begin
            if (grant) begin
                out_valid <= 1'b1;
                out_vc    <= gvc;
                out_data  <= gdata;
            end else if (out_valid && out_ready) begin
                out_valid <= 1'b0;
                out_vc    <= 2'd0;
                out_data  <= 8'd0;
            end else begin
                out_valid <= out_valid;
                out_vc    <= out_vc;
                out_data  <= out_data;
            end
            last_r <= next_last;
            run_r  <= next_run;
        end
    end

    // ------------------------------------------------------------------
    // Per-VC buffer (4.6, 4.7) and credits (4.8)
    // ------------------------------------------------------------------
    genvar v;
    generate
        for (v = 0; v < 3; v = v + 1) begin : g_vc
            wire [1:0] cnt_v   = cnt_r[2*v+1 -: 2];
            wire [2:0] cred_v  = cred_r[3*v+2 -: 3];
            wire [7:0] wdata   = in_data[8*v+7 -: 8];
            wire       wr      = in_valid[v] && (cnt_v < 2'd2);
            wire       rm      = grant_v[v];
            wire [2:0] base    = (cfg_we && (cfg_vc == v)) ? cfg_credits : cred_v;
            wire [3:0] sum     = {1'b0, base} + {3'b000, cr_ret[v]};
            wire [3:0] dec     = rm ? ((sum == 4'd0) ? 4'd0 : (sum - 4'd1)) : sum;
            wire [2:0] cred_n  = (dec > 4'd7) ? 3'd7 : dec[2:0];

            always @(posedge clk) begin
                if (!rst_n) begin
                    cnt_r[2*v+1 -: 2]  <= 2'd0;
                    cred_r[3*v+2 -: 3] <= 3'd4;
                    b0_r[8*v+7 -: 8]   <= 8'd0;
                    b1_r[8*v+7 -: 8]   <= 8'd0;
                end else begin
                    cred_r[3*v+2 -: 3] <= cred_n;
                    if (flush[v]) begin
                        // every pre-edge byte is discarded; a byte written at
                        // this edge survives and becomes the only byte
                        if (wr) begin
                            cnt_r[2*v+1 -: 2] <= 2'd1;
                            b0_r[8*v+7 -: 8]  <= wdata;
                            b1_r[8*v+7 -: 8]  <= b1_r[8*v+7 -: 8];
                        end else begin
                            cnt_r[2*v+1 -: 2] <= 2'd0;
                            b0_r[8*v+7 -: 8]  <= b0_r[8*v+7 -: 8];
                            b1_r[8*v+7 -: 8]  <= b1_r[8*v+7 -: 8];
                        end
                    end else if (rm && wr) begin
                        // rm implies cnt_v >= 1, wr implies cnt_v < 2 -> cnt_v == 1
                        cnt_r[2*v+1 -: 2] <= 2'd1;
                        b0_r[8*v+7 -: 8]  <= wdata;
                        b1_r[8*v+7 -: 8]  <= b1_r[8*v+7 -: 8];
                    end else if (rm) begin
                        if (cnt_v == 2'd2) begin
                            cnt_r[2*v+1 -: 2] <= 2'd1;
                            b0_r[8*v+7 -: 8]  <= b1_r[8*v+7 -: 8];
                        end else begin
                            cnt_r[2*v+1 -: 2] <= 2'd0;
                            b0_r[8*v+7 -: 8]  <= b0_r[8*v+7 -: 8];
                        end
                        b1_r[8*v+7 -: 8] <= b1_r[8*v+7 -: 8];
                    end else if (wr) begin
                        if (cnt_v == 2'd0) begin
                            cnt_r[2*v+1 -: 2] <= 2'd1;
                            b0_r[8*v+7 -: 8]  <= wdata;
                            b1_r[8*v+7 -: 8]  <= b1_r[8*v+7 -: 8];
                        end else begin
                            cnt_r[2*v+1 -: 2] <= 2'd2;
                            b0_r[8*v+7 -: 8]  <= b0_r[8*v+7 -: 8];
                            b1_r[8*v+7 -: 8]  <= wdata;
                        end
                    end else begin
                        cnt_r[2*v+1 -: 2] <= cnt_v;
                        b0_r[8*v+7 -: 8]  <= b0_r[8*v+7 -: 8];
                        b1_r[8*v+7 -: 8]  <= b1_r[8*v+7 -: 8];
                    end
                end
            end
        end
    endgenerate

endmodule
