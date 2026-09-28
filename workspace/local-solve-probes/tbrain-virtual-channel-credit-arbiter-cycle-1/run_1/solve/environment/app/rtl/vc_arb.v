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
    // Per-VC state, packed to keep everything in plain flip-flops.
    reg [23:0] buf0;   // oldest byte of each VC, bits 8v+7:8v
    reg [23:0] buf1;   // newest byte of each VC
    reg [5:0]  cntv;   // bits 2v+1:2v : 0, 1 or 2 bytes buffered
    reg [8:0]  credv;  // bits 3v+2:3v : credit count 0..7
    reg [1:0]  last;   // VC of most recent grant
    reg        run1;   // 1 when run == 1, 0 when run == 2

    assign credits = credv;

    // 3.2 in_ready
    assign in_ready[0] = (cntv[1:0] != 2'd2);
    assign in_ready[1] = (cntv[3:2] != 2'd2);
    assign in_ready[2] = (cntv[5:4] != 2'd2);

    // 4.1 grant opportunity
    wire opp = (~out_valid) | out_ready;

    // 4.2 eligibility (registers before the edge only)
    wire [2:0] elig;
    assign elig[0] = (cntv[1:0] != 2'd0) && (credv[2:0] != 3'd0) && !flush[0];
    assign elig[1] = (cntv[3:2] != 2'd0) && (credv[5:3] != 3'd0) && !flush[1];
    assign elig[2] = (cntv[5:4] != 2'd0) && (credv[8:6] != 3'd0) && !flush[2];

    // round-robin order last+1, last+2, last (modulo 3)
    wire [1:0] c1 = (last == 2'd2) ? 2'd0 : (last + 2'd1);
    wire [1:0] c2 = (last == 2'd0) ? 2'd2 : (last - 2'd1);

    reg        gvalid;   // a grant is made at this edge
    reg [1:0]  gsel;     // granted VC
    reg        nrun1;    // next value of run1
    reg [1:0]  nlast;    // next value of last

    // 4.3 / 4.4 selection
    always @* begin
        gvalid = 1'b0;
        gsel   = 2'd0;
        nrun1  = run1;
        nlast  = last;
        if (opp) begin
            if (run1 && elig[last]) begin
                gvalid = 1'b1;
                gsel   = last;
                nrun1  = 1'b0;          // run becomes 2
            end else begin
                if (elig[c1]) begin
                    gvalid = 1'b1;
                    gsel   = c1;
                end else if (elig[c2]) begin
                    gvalid = 1'b1;
                    gsel   = c2;
                end else if (elig[last]) begin
                    gvalid = 1'b1;
                    gsel   = last;
                end
                if (gvalid) begin
                    nrun1 = 1'b1;       // run becomes 1
                    nlast = gsel;
                end
            end
        end
        if (!gvalid && flush[last]) begin
            nrun1 = 1'b0;               // 4.4: run becomes 2
        end
    end

    // oldest byte of the granted VC
    reg [7:0] gdata;
    always @* begin
        case (gsel)
            2'd0:    gdata = buf0[7:0];
            2'd1:    gdata = buf0[15:8];
            default: gdata = buf0[23:16];
        endcase
    end

    integer v;
    reg        wr;      // this VC accepts a byte at this edge
    reg        gr;      // this VC is granted at this edge
    reg [7:0]  ibyte;
    reg [1:0]  ccnt;
    reg [2:0]  base;
    reg [2:0]  nc;

    always @(posedge clk) begin
        if (!rst_n) begin
            // 5. reset
            buf0      <= 24'd0;
            buf1      <= 24'd0;
            cntv      <= 6'd0;
            credv     <= 9'o444;
            out_valid <= 1'b0;
            out_vc    <= 2'd0;
            out_data  <= 8'd0;
            last      <= 2'd2;
            run1      <= 1'b0;   // run = 2
        end else begin
            last <= nlast;
            run1 <= nrun1;

            // 4.5 output register
            if (gvalid) begin
                out_valid <= 1'b1;
                out_vc    <= gsel;
                out_data  <= gdata;
            end else if (out_valid && out_ready) begin
                out_valid <= 1'b0;
                out_vc    <= 2'd0;
                out_data  <= 8'd0;
            end

            for (v = 0; v < 3; v = v + 1) begin
                ccnt  = cntv[2*v +: 2];
                ibyte = in_data[8*v +: 8];
                wr    = in_valid[v] && (ccnt != 2'd2);
                gr    = gvalid && (gsel == v);

                // 4.6 / 4.7 buffer
                if (flush[v]) begin
                    if (wr) begin
                        buf0[8*v +: 8] <= ibyte;
                        cntv[2*v +: 2] <= 2'd1;
                    end else begin
                        cntv[2*v +: 2] <= 2'd0;
                    end
                end else if (gr && wr) begin
                    // ccnt is 1 here (a full buffer never accepts a byte)
                    buf0[8*v +: 8] <= (ccnt == 2'd1) ? ibyte : buf1[8*v +: 8];
                    if (ccnt != 2'd1) begin
                        buf1[8*v +: 8] <= ibyte;
                    end
                    cntv[2*v +: 2] <= ccnt;
                end else if (gr) begin
                    buf0[8*v +: 8] <= buf1[8*v +: 8];
                    cntv[2*v +: 2] <= ccnt - 2'd1;
                end else if (wr) begin
                    if (ccnt == 2'd0) begin
                        buf0[8*v +: 8] <= ibyte;
                    end else begin
                        buf1[8*v +: 8] <= ibyte;
                    end
                    cntv[2*v +: 2] <= ccnt + 2'd1;
                end

                // 4.8 credits
                base = (cfg_we && (cfg_vc == v)) ? cfg_credits
                                                      : credv[3*v +: 3];
                if (gr && !cr_ret[v]) begin
                    nc = (base == 3'd0) ? 3'd0 : (base - 3'd1);
                end else if (!gr && cr_ret[v]) begin
                    nc = (base == 3'd7) ? 3'd7 : (base + 3'd1);
                end else begin
                    nc = base;
                end
                credv[3*v +: 3] <= nc;
            end
        end
    end
endmodule
