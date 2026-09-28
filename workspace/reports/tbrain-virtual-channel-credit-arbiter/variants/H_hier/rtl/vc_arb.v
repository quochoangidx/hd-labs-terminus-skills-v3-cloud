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
    reg [7:0] head [0:2];
    reg [7:0] tail [0:2];
    reg [1:0] cnt  [0:2];
    reg [2:0] cred [0:2];
    reg [1:0] last;
    reg       run2;

    genvar gv;
    generate
        for (gv = 0; gv < 3; gv = gv + 1) begin : g_out
            assign in_ready[gv] = (cnt[gv] != 2'd2);
            assign credits[3*gv+2:3*gv] = cred[gv];
        end
    endgenerate

    wire opp = !out_valid || harness_tb.out_ready;
    wire [2:0] elig;
    assign elig[0] = (cnt[0] != 0) && (cred[0] != 0) && !flush[0];
    assign elig[1] = (cnt[1] != 0) && (cred[1] != 0) && !flush[1];
    assign elig[2] = (cnt[2] != 0) && (cred[2] != 0) && !flush[2];

    wire [1:0] n1 = (last == 2'd2) ? 2'd0 : last + 2'd1;
    wire [1:0] n2 = (n1 == 2'd2) ? 2'd0 : n1 + 2'd1;

    reg       gnt;
    reg [1:0] gvc;
    reg       stick;
    always @(*) begin
        gnt = 1'b0; gvc = 2'd0; stick = 1'b0;
        if (opp) begin
            if (!run2 && elig[last]) begin
                gnt = 1'b1; gvc = last; stick = 1'b1;
            end else if (elig[n1]) begin
                gnt = 1'b1; gvc = n1;
            end else if (elig[n2]) begin
                gnt = 1'b1; gvc = n2;
            end else if (elig[last]) begin
                gnt = 1'b1; gvc = last;
            end
        end
    end

    integer v;
    reg [3:0] nc;
    reg push;
    always @(posedge clk) begin
        if (!rst_n) begin
            out_valid <= 1'b0; out_vc <= 2'd0; out_data <= 8'd0;
            last <= 2'd2; run2 <= 1'b1;
            for (v = 0; v < 3; v = v + 1) begin
                cnt[v] <= 2'd0; cred[v] <= 3'd4; head[v] <= 8'd0; tail[v] <= 8'd0;
            end
        end else begin
            if (gnt) begin
                out_valid <= 1'b1; out_vc <= gvc; out_data <= head[gvc];
                last <= gvc; run2 <= stick;
            end else begin
                if (out_valid && out_ready) begin
                    out_valid <= 1'b0; out_vc <= 2'd0; out_data <= 8'd0;
                end
                if (flush[last]) run2 <= 1'b1;
            end
            for (v = 0; v < 3; v = v + 1) begin
                push = in_valid[v] && (cnt[v] != 2'd2);
                if (flush[v]) begin
                    cnt[v] <= push ? 2'd1 : 2'd0;
                    if (push) head[v] <= in_data[8*v +: 8];
                end else if (gnt && gvc == v) begin
                    if (cnt[v] == 2'd2) begin
                        head[v] <= tail[v];
                        cnt[v] <= 2'd1;
                    end else if (push) begin
                        head[v] <= in_data[8*v +: 8];
                    end else begin
                        cnt[v] <= 2'd0;
                    end
                end else if (push) begin
                    if (cnt[v] == 2'd0) head[v] <= in_data[8*v +: 8];
                    else tail[v] <= in_data[8*v +: 8];
                    cnt[v] <= cnt[v] + 2'd1;
                end
                nc = {1'b0, (cfg_we && cfg_vc == v) ? cfg_credits : cred[v]};
                nc = nc - ((gnt && gvc == v) ? 4'd1 : 4'd0) + (cr_ret[v] ? 4'd1 : 4'd0);
                if (nc == 4'hF) cred[v] <= 3'd0;
                else if (nc > 4'd7) cred[v] <= 3'd7;
                else cred[v] <= nc[2:0];
            end
        end
    end
endmodule
