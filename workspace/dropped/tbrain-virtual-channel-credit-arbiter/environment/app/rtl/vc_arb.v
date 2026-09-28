// vc_arb: three-channel credit-based link transmit arbiter.
// Behaviour is defined in /app/docs/spec.md. Not yet implemented.
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
    assign in_ready = 3'b000;
    assign credits  = 9'd0;
    always @(posedge clk) begin
        out_valid <= 1'b0;
        out_vc    <= 2'd0;
        out_data  <= 8'd0;
    end
endmodule
