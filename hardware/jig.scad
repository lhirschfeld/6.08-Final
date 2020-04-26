INCH_TO_MM = 25.4;

ENCODER_OD = 46;
BOLT_CIRCLE_DIAMETER = 30;
MOTOR_TOP_OFFSET = 5;


square([4*INCH_TO_MM, 4*INCH_TO_MM]);

translate([5*INCH_TO_MM,0]) {
    difference() {
        square([67,70]);
        
        translate([67/2,70]) circle()
    }
}