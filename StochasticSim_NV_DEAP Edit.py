from WBT.whitebox_tools import WhiteboxTools
from timeit import default_timer as timer
from datetime import timedelta

wbt = WhiteboxTools()
wbt.verbose = False
wbt.set_working_dir(r"F:\stocasticSensitvityLayers(MerseyRiverStudy)")

# input parameters
dem = "merseyMosaic.tif"
land_use = "LandUse_ReclassifiedInvert.tif"
river = "RasterizedRiver.tif"
prox_to_dams = "Proximity_Dams.tif"
slope = "slopeTemp.tif" #slope,hand,and ddts are just temporary files (i.e., they get overwritten each time)
hand = "handTemp.tif"
ddts = "ddtsTemp.tif"
low_vuln_thresh = 15 #this was arbitrary; it's up to you to decide an appropriate vulnerability threshold
mod_vuln_thresh = 25
high_vuln_thresh = 40
rmse = 6.6 # this is the RMSE of your DEM
gauss_filt_size = 3.0
num_iterations = 50 # how many times do you want to run this simulation

# create new base raster initialized with 0 values
# This raster will hold the values for each cell that determines whether a cell is vulnerable or not, what we're calling the vulnerability frequency here.
# Each iteration, if a cell is vulnerable (as defined by your threshold), the frequency will be incremented by 1.
start = timer()
wbt.new_raster_from_base(
    base = dem, # using the dem as the base ensures that the extent and cell size of the output is the same as the dem.
    output = "low_vulnerability_freq.tif",
    value = 0.0
)

wbt.new_raster_from_base(
    base = dem, # using the dem as the base ensures that the extent and cell size of the output is the same as the dem.
    output = "mod_vulnerability_freq.tif",
    value = 0.0
)

wbt.new_raster_from_base(
    base = dem, # using the dem as the base ensures that the extent and cell size of the output is the same as the dem.
    output = "high_vulnerability_freq.tif",
    value = 0.0
)


# perform stochastic (i.e. Monte Carlo) simulation. Notice that we don't change the names of inputs/outputs as we iterate, 
# so after each iteration, we are overwriting the previous files and thus not having to store hundreds or thousands of rasters
# You will end up with just one raster for each input/output, and it will represent the last iteration.
for i in range(num_iterations):

    print(f"Iteration {i+1} of {num_iterations}...",end='\r')

    #generate a raster of random values
    wbt.random_field(
        base = dem,
        output = "random1.tif"
    )

    # add spatial autocorrelation with the gaussian filter, because error in DEMs is autocorrelated.
    wbt.gaussian_filter(
        i = "random1.tif",
        output = "random2.tif",
        sigma=gauss_filt_size
    )

    # multiply the spatially autocorrelated random field by your RMSE to produce an error field corresponding to the possible error values, as given by the RMSE
    wbt.multiply(
        input1 = "random2.tif",
        input2 = rmse,
        output = "error_model.tif"
    )

    # now add the generated error to the dem
    wbt.add(
        input1 = "error_model.tif",
        input2 = dem,
        output = "curr_dem_iter.tif"
    )

    # MCE workflow goes here. Use the current dem iteration to derive your MCE variables, then combine them in an MCE
    # weights = land use = 0.270, slope = 0.226, HAND = 0.221, river = 0.165, dam proximity  0.118
    wbt.slope(
        dem = "curr_dem_iter.tif",
        output = slope
    )

    wbt.breach_depressions_least_cost(
        dem="curr_dem_iter.tif",
        output="breached_error_dem.tif",
        dist=128
    )

    wbt.elevation_above_stream(
        dem ="breached_error_dem.tif",
        streams = river,
        output = hand
    )

    wbt.downslope_distance_to_stream(
        dem="breached_error_dem.tif",
        streams=river,
        output=ddts
    )

    # Weighted Overlay tool, which will produce your final MCE raster.
    wbt.weighted_overlay(
        factors=f"{slope};{hand};{ddts};{land_use};{prox_to_dams}",
        weights="0.226;0.221;0.165;0.270;0.118", #these must be in the same order that the factors are entered...
        cost="false;false;false;false;false",
        output="final_MCE.tif",
        scale_max=100 #because this tool rescales the data for you, use the original data as your inputs, not your rescaled data
    )
    

#Vulnerability thresholds for analysis
    wbt.greater_than(
        input1 = "final_MCE.tif", # this variable will be the final product of your MCE workflow
        input2 = low_vuln_thresh, # whatever your threshold is for vulnerability MCE, this will produce a boolean raster where it's either vulnerable (1) or not (0)
        output = "low_vuln_cells.tif"
    )

    # increment vulnerability frequency by this iteration's vulnerable cells
    # notice that a new raster is not being produced. Instead, vulnerable_freq.tif is being updated.
    wbt.in_place_add(
        input1 = "low_vulnerability_freq.tif",
        input2 = "low_vuln_cells.tif"
    )
    
    
    wbt.greater_than(
        input1 = "final_MCE.tif", # this variable will be the final product of your MCE workflow
        input2 = mod_vuln_thresh, # whatever your threshold is for vulnerability MCE, this will produce a boolean raster where it's either vulnerable (1) or not (0)
        output = "mod_vuln_cells.tif"
    )

    # increment vulnerability frequency by this iteration's vulnerable cells
    # notice that a new raster is not being produced. Instead, vulnerable_freq.tif is being updated.
    wbt.in_place_add(
        input1 = "mod_vulnerability_freq.tif",
        input2 = "mod_vuln_cells.tif"
    )

    wbt.greater_than(
        input1 = "final_MCE.tif", # this variable will be the final product of your MCE workflow
        input2 = high_vuln_thresh, # whatever your threshold is for vulnerability MCE, this will produce a boolean raster where it's either vulnerable (1) or not (0)
        output = "high_vuln_cells.tif"
    )

    # increment vulnerability frequency by this iteration's vulnerable cells
    # notice that a new raster is not being produced. Instead, vulnerable_freq.tif is being updated.
    wbt.in_place_add(
        input1 = "high_vulnerability_freq.tif",
        input2 = "high_vuln_cells.tif"
    )


# Finally, calculate uncertainty by dividing the vulnerability frequency by the number of iterations
print("\nCalculating uncertainty...")
wbt.divide(
    input1 = "low_vulnerability_freq.tif",
    input2 = num_iterations,
    output = "low_final_uncertainty.tif" 
)

wbt.divide(
    input1 = "mod_vulnerability_freq.tif",
    input2 = num_iterations,
    output = "mod_final_uncertainty.tif" 
)

wbt.divide(
    input1 = "high_vulnerability_freq.tif",
    input2 = num_iterations,
    output = "high_final_uncertainty.tif" 
)

end = timer()
final_time = str(timedelta(seconds = end - start))
print(f"Stochastic simulation completed in: {final_time[:-4]} seconds.")