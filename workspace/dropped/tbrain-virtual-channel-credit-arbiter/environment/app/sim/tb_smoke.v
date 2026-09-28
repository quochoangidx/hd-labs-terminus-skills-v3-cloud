// Directed smoke bench: reset, one byte on VC 0, drain it.
module tb_smoke;
    reg clk = 0;
    always #5 clk = ~clk;
    reg rst_n = 0; reg [2:0] in_valid = 0; reg [23:0] in_data = 0; reg out_ready = 0;
    reg [2:0] cr_ret = 0; reg [2:0] flush = 0; reg cfg_we = 0; reg [1:0] cfg_vc = 0; reg [2:0] cfg_credits = 0;
    wire [2:0] in_ready; wire out_valid; wire [1:0] out_vc; wire [7:0] out_data; wire [8:0] credits;
    integer errors = 0;
    vc_arb dut(.clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_data(in_data), .in_ready(in_ready),
               .out_valid(out_valid), .out_vc(out_vc), .out_data(out_data), .out_ready(out_ready),
               .cr_ret(cr_ret), .flush(flush), .cfg_we(cfg_we), .cfg_vc(cfg_vc),
               .cfg_credits(cfg_credits), .credits(credits));
    task check(input [2:0] rdy, input ov, input [1:0] vc, input [7:0] d, input [8:0] cr);
        if ({in_ready, out_valid, out_vc, out_data, credits} !== {rdy, ov, vc, d, cr}) begin
            $display("MISMATCH t=%0t got rdy=%b ov=%b vc=%0d d=%h cr=%o  want rdy=%b ov=%b vc=%0d d=%h cr=%o",
                     $time, in_ready, out_valid, out_vc, out_data, credits, rdy, ov, vc, d, cr);
            errors = errors + 1;
        end
    endtask
    initial begin
        @(negedge clk); @(negedge clk);
        check(3'b111, 0, 0, 8'h00, 9'o444);
        rst_n = 1; in_valid = 3'b001; in_data = 24'h0000a5;
        @(negedge clk);               // byte written into VC 0
        check(3'b111, 0, 0, 8'h00, 9'o444);
        in_valid = 0;
        @(negedge clk);               // VC 0 granted, one credit spent
        check(3'b111, 1, 0, 8'ha5, 9'o443);
        out_ready = 1;
        @(negedge clk);               // byte leaves
        check(3'b111, 0, 0, 8'h00, 9'o443);
        if (errors == 0) $display("SMOKE PASS"); else $display("SMOKE FAIL (%0d)", errors);
        $finish;
    end
endmodule
