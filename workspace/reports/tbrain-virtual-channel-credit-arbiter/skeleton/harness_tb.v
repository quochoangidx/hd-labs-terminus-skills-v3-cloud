`timescale 1ns/1ps
module harness_tb;
    reg clk = 0;
    reg rst_n; reg [2:0] in_valid; reg [23:0] in_data; reg out_ready;
    reg [2:0] cr_ret; reg [2:0] flush; reg cfg_we; reg [1:0] cfg_vc; reg [2:0] cfg_credits;
    wire [2:0] in_ready; wire out_valid; wire [1:0] out_vc; wire [7:0] out_data; wire [8:0] credits;
    vc_arb dut(.clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_data(in_data), .in_ready(in_ready),
               .out_valid(out_valid), .out_vc(out_vc), .out_data(out_data), .out_ready(out_ready),
               .cr_ret(cr_ret), .flush(flush), .cfg_we(cfg_we), .cfg_vc(cfg_vc),
               .cfg_credits(cfg_credits), .credits(credits));
    reg [40:0] mem [0:65535];
    integer n, i;
    reg [1023:0] fname;
    initial begin
        if (!$value$plusargs("stim=%s", fname)) $finish;
        if (!$value$plusargs("n=%d", n)) $finish;
        $readmemh(fname, mem);
        for (i = 0; i < n; i = i + 1) begin
            {rst_n, in_valid, in_data, out_ready, cr_ret, flush, cfg_we, cfg_vc, cfg_credits} = mem[i];
            #5 clk = 1;
            #5 clk = 0;
            $display("T %0d %0d %0d %0d %0d %0d", i, in_ready, out_valid, out_vc, out_data, credits);
        end
        $display("END");
        $finish;
    end
endmodule
